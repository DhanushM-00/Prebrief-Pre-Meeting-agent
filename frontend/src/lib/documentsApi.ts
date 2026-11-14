/**
 * Document library API client — uses centralized http client and anonymous session cookies.
 */
import { http, parseApiError, API_BASE } from './http'

export interface DocumentItem {
  id: string
  originalFilename: string
  contentType: string
  extension: string
  sizeBytes: number
  status: string
  statusMessage?: string | null
  category?: string | null
  pageCount?: number | null
  wordCount?: number | null
  hasExtractedText: boolean
  hasIntelligence: boolean
  createdAt: string
  processedAt?: string | null
}

export interface DocumentDetail extends DocumentItem {
  extractedTextPreview?: string | null
  intelligence?: unknown
}

function mapDoc(raw: Record<string, unknown>): DocumentItem {
  return {
    id: String(raw.id ?? ''),
    originalFilename: String(raw.originalFilename ?? raw.original_filename ?? ''),
    contentType: String(raw.contentType ?? raw.content_type ?? ''),
    extension: String(raw.extension ?? ''),
    sizeBytes: Number(raw.sizeBytes ?? raw.size_bytes ?? 0),
    status: String(raw.status ?? ''),
    statusMessage: (raw.statusMessage ?? raw.status_message) as string | null | undefined,
    category: (raw.category as string | null | undefined) ?? null,
    pageCount: (raw.pageCount ?? raw.page_count) as number | null | undefined,
    wordCount: (raw.wordCount ?? raw.word_count) as number | null | undefined,
    hasExtractedText: Boolean(raw.hasExtractedText ?? raw.has_extracted_text),
    hasIntelligence: Boolean(raw.hasIntelligence ?? raw.has_intelligence),
    createdAt: String(raw.createdAt ?? raw.created_at ?? ''),
    processedAt: (raw.processedAt ?? raw.processed_at) as string | null | undefined,
  }
}

export async function listDocuments(params?: {
  category?: string
  status?: string
  q?: string
}): Promise<{ items: DocumentItem[]; total: number }> {
  const q = new URLSearchParams()
  if (params?.category) q.set('category', params.category)
  if (params?.status) q.set('status', params.status)
  if (params?.q) q.set('q', params.q)
  const qs = q.toString()
  const data = await http.get<{ items?: unknown[]; total?: number; documents?: unknown[] }>(
    `/documents${qs ? `?${qs}` : ''}`,
  )
  const list = data.items ?? data.documents ?? []
  return {
    items: list.map((d) => mapDoc(d as Record<string, unknown>)),
    total: data.total ?? list.length,
  }
}

export async function uploadDocument(
  file: File,
  opts?: string | { category?: string; signal?: AbortSignal; onProgress?: (pct: number) => void },
): Promise<DocumentItem> {
  const options = typeof opts === 'string' ? { category: opts } : opts || {}
  return new Promise((resolve, reject) => {
    if (!API_BASE) {
      reject(new Error('Backend is not configured. Set VITE_API_BASE_URL.'))
      return
    }
    const form = new FormData()
    form.append('file', file)
    if (options.category) form.append('category', options.category)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/documents`)
    xhr.withCredentials = true
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && options.onProgress) options.onProgress(Math.round((e.loaded / e.total) * 100))
    }
    if (options.signal) {
      if (options.signal.aborted) { xhr.abort(); return }
      options.signal.addEventListener('abort', () => xhr.abort())
    }
    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(mapDoc(JSON.parse(xhr.responseText)))
        } catch (err) {
          reject(err)
        }
      } else {
        try {
          const fake = {
            ok: false,
            status: xhr.status,
            statusText: xhr.statusText,
            json: async () => JSON.parse(xhr.responseText),
            headers: { get: () => null },
          } as unknown as Response
          reject(await parseApiError(fake))
        } catch {
          reject(new Error(xhr.statusText || `Upload failed (${xhr.status})`))
        }
      }
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(form)
  })
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  const raw = await http.get<Record<string, unknown>>(`/documents/${id}`)
  return {
    ...mapDoc(raw),
    extractedTextPreview: (raw.extractedTextPreview ?? raw.extracted_text_preview) as string | null | undefined,
    intelligence: raw.intelligence ?? null,
  }
}

export async function deleteDocument(id: string): Promise<void> {
  await http.delete(`/documents/${id}`)
}

export async function reprocessDocument(id: string): Promise<void> {
  await http.post(`/documents/${id}/reprocess`)
}

export async function downloadDocument(id: string, filename: string): Promise<void> {
  const blob = await http.blob(`/documents/${id}/download`)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export async function chatDocuments(
  question: string,
  documentIds?: string[],
): Promise<{ answer: string; citations: Array<{ documentName?: string; location?: string; excerpt?: string }> }> {
  const data = await http.post<{
    answer: string
    citations?: Array<Record<string, unknown>>
  }>('/documents/chat', { question, documentIds })
  return {
    answer: data.answer,
    citations: (data.citations || []).map((c) => ({
      documentName: (c.documentName ?? c.document_name) as string | undefined,
      location: c.location as string | undefined,
      excerpt: c.excerpt as string | undefined,
    })),
  }
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}
