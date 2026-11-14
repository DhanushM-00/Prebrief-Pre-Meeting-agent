import { useMemo, useState } from 'react'
import { ExternalLink, ImageOff, X, ZoomIn } from 'lucide-react'
import { clsx } from 'clsx'
import type { ImageAsset } from '../types'
import { Badge, Button } from './ui'

const CATEGORY_LABEL: Record<string, string> = {
  logo: 'Logo',
  headquarters: 'Headquarters',
  office: 'Office',
  product: 'Product',
  event: 'Event',
  brand: 'Brand',
  profile: 'Profile',
  leadership: 'Leadership',
  public: 'Public',
}

function SafeImage({
  src,
  alt,
  className,
  onClick,
}: {
  src: string
  alt: string
  className?: string
  onClick?: () => void
}) {
  const [failed, setFailed] = useState(false)
  if (failed) {
    return (
      <div className={clsx('flex items-center justify-center bg-surface-3 text-faint', className)}>
        <ImageOff size={20} />
      </div>
    )
  }
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      className={className}
      onError={() => setFailed(true)}
      onClick={onClick}
    />
  )
}

export function ImageGallery({
  images,
  subject,
  subjectType,
}: {
  images: ImageAsset[]
  subject: string
  subjectType: string
}) {
  const [filter, setFilter] = useState<string>('all')
  const [lightbox, setLightbox] = useState<ImageAsset | null>(null)

  const categories = useMemo(() => {
    const s = new Set(images.map((i) => i.category))
    return ['all', ...Array.from(s)]
  }, [images])

  const filtered = filter === 'all' ? images : images.filter((i) => i.category === filter)

  if (!images.length) {
    return (
      <div className="rounded-xl border border-line bg-surface px-4 py-8 text-center text-sm text-muted">
        No verified images found for {subject}. Image search uses provider results with entity checks —
        weak matches are excluded on purpose.
      </div>
    )
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-ink">
            {subjectType === 'person' ? 'Person' : 'Company'} visual profile
          </h2>
          <p className="text-[11px] text-faint">
            Images from search providers · attribution required · verify licensing before reuse
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setFilter(c)}
              className={clsx(
                'rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors',
                filter === c ? 'bg-accent text-white' : 'bg-surface-2 text-muted hover:text-ink',
              )}
            >
              {c === 'all' ? 'All' : CATEGORY_LABEL[c] || c}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {filtered.map((img) => (
          <figure
            key={img.id}
            className="group overflow-hidden rounded-xl border border-line bg-surface shadow-card"
          >
            <div className="relative aspect-[4/3] bg-surface-3">
              <SafeImage
                src={img.thumbnailUrl || img.url}
                alt={img.altText || img.title || subject}
                className="h-full w-full object-cover transition-transform group-hover:scale-[1.02]"
              />
              <button
                type="button"
                onClick={() => setLightbox(img)}
                className="absolute right-2 top-2 rounded-lg bg-black/50 p-1.5 text-white opacity-0 transition-opacity group-hover:opacity-100"
                aria-label="View full size"
              >
                <ZoomIn size={14} />
              </button>
            </div>
            <figcaption className="space-y-1 p-2.5">
              <div className="flex items-center gap-1.5">
                <Badge tone="neutral">{CATEGORY_LABEL[img.category] || img.category}</Badge>
                {img.confidence && (
                  <span className="text-[10px] text-faint">{img.confidence}</span>
                )}
              </div>
              <p className="line-clamp-2 text-[11px] text-muted">
                {img.title || img.altText || subject}
              </p>
              <div className="flex items-center justify-between gap-1 text-[10px] text-faint">
                <span className="truncate">{img.attribution || img.sourceName || 'Source'}</span>
                {img.sourcePageUrl && (
                  <a
                    href={img.sourcePageUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex shrink-0 items-center gap-0.5 hover:text-ink"
                  >
                    Source <ExternalLink size={9} />
                  </a>
                )}
              </div>
            </figcaption>
          </figure>
        ))}
      </div>

      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
          onClick={() => setLightbox(null)}
        >
          <div
            className="relative max-h-full max-w-4xl overflow-auto rounded-2xl bg-surface p-3 shadow-pop"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className="absolute right-3 top-3 z-10 rounded-lg bg-surface-2 p-1.5 text-muted hover:text-ink"
              onClick={() => setLightbox(null)}
            >
              <X size={16} />
            </button>
            <SafeImage
              src={lightbox.url}
              alt={lightbox.altText || lightbox.title || subject}
              className="max-h-[70vh] w-full rounded-lg object-contain"
            />
            <div className="mt-3 space-y-1 px-1 text-sm">
              <p className="font-medium text-ink">{lightbox.title || subject}</p>
              <p className="text-xs text-muted">
                {lightbox.attribution || lightbox.sourceName}
                {lightbox.licenseNote ? ` · ${lightbox.licenseNote}` : ''}
              </p>
              <div className="flex gap-2 pt-1">
                {lightbox.sourcePageUrl && (
                  <Button size="sm" variant="ghost" as-child={undefined}>
                    <a href={lightbox.sourcePageUrl} target="_blank" rel="noopener noreferrer">
                      Open source page
                    </a>
                  </Button>
                )}
                <a
                  href={lightbox.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-accent-text hover:underline"
                >
                  Open image <ExternalLink size={11} />
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
