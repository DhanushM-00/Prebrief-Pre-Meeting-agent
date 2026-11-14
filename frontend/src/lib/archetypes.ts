import type { Archetype, PersonArchetype } from './corpus'

export const COMPANY_ARCHETYPES: Archetype[] = [
  'saas', 'fintech', 'ai', 'ecommerce', 'hardware', 'healthcare',
  'consumer', 'marketplace', 'devtools', 'energy', 'media',
]

export const PERSON_ARCHETYPES: PersonArchetype[] = [
  'founder', 'exec', 'investor', 'operator', 'creator', 'advisor',
]

/** Stable demo companies — useful as one-tap examples. */
export const DEMO_COMPANIES: { name: string; archetype: Archetype }[] = [
  { name: 'Northwind Robotics', archetype: 'hardware' },
  { name: 'Helio Grid', archetype: 'energy' },
  { name: 'Quantipay', archetype: 'fintech' },
  { name: 'Lumen Bio', archetype: 'healthcare' },
  { name: 'Cinderworks', archetype: 'ai' },
  { name: 'Arcadia Market', archetype: 'marketplace' },
]

/** Stable demo people. */
export const DEMO_PEOPLE: { name: string; archetype: PersonArchetype }[] = [
  { name: 'Ada Chen', archetype: 'founder' },
  { name: 'Marcus Reyes', archetype: 'exec' },
  { name: 'Priya Kapoor', archetype: 'investor' },
  { name: 'Tomas Lindqvist', archetype: 'operator' },
]

/**
 * Maps a known demo name to its archetype so repeated runs stay coherent.
 * Unknown names fall back to a seeded pick.
 */
export const ARCHETYPE_BY_SUFFIX: Record<string, Archetype> = Object.fromEntries(
  DEMO_COMPANIES.map((c) => [c.name, c.archetype]),
)
