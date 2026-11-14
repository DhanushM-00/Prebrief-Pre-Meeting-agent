/* ------------------------------------------------------------------ *
 * Demo corpus — synthetic vocabulary + headline templates.
 *
 * IMPORTANT: every name, company and figure produced here is fabricated.
 * The demo dataset exists so the UI can be exercised without a backend.
 * It is never presented as real intelligence (see DEMO badge in the UI).
 * ------------------------------------------------------------------ */

export type Archetype =
  | 'saas'
  | 'fintech'
  | 'ai'
  | 'ecommerce'
  | 'hardware'
  | 'healthcare'
  | 'consumer'
  | 'marketplace'
  | 'devtools'
  | 'energy'
  | 'media'

export type PersonArchetype =
  | 'founder'
  | 'exec'
  | 'investor'
  | 'operator'
  | 'creator'
  | 'advisor'

export const COMPANY_PREFIX = [
  'Northwind', 'Helio', 'Quant', 'Lumen', 'Vertex', 'Arcadia', 'Cobalt', 'Juniper', 'Meridian',
  'Solstice', 'Vantage', 'Kestrel', 'Aster', 'Onyx', 'Cobalt', 'Halcyon', 'Terra', 'Pulse',
  'Ember', 'Aurora', 'Lattice', 'Nova', 'Summit', 'Cinder', 'Beacon', 'Orbital', 'Pinnacle',
]

export const COMPANY_SUFFIX = [
  'Labs', 'Systems', 'Robotics', 'Grid', 'Pay', 'Health', 'Bio', 'AI', 'Works', 'Cloud',
  'Dynamics', 'Collective', 'Foundry', 'Analytics', 'Networks', 'Studio', 'Capital', 'Logistics',
]

export const FIRST_NAMES = [
  'Ada', 'Marcus', 'Priya', 'Elena', 'Tomas', 'Yuki', 'Nadia', 'Owen', 'Leila', 'Ravi',
  'Sofia', 'Jonas', 'Amara', 'Felix', 'Mira', 'Dmitri', 'Hana', 'Omar', 'Cora', 'Idris',
  'Beatriz', 'Kenji', 'Naomi', 'Rafael', 'Ingrid', 'Samuel', 'Zara', 'Mateo', 'Ines', 'Kai',
]

export const LAST_NAMES = [
  'Chen', 'Reyes', 'Okonkwo', 'Lindqvist', 'Alvarez', 'Nakamura', 'Haddad', 'Whitfield',
  'Moreau', 'Kapoor', 'Bergström', 'Oyelaran', 'Tanaka', 'Vasquez', 'Novak', 'Ferreira',
  'Sørensen', 'Ahluwalia', 'Kowalski', 'Dubois', 'Mensah', 'Rossi', 'Petrov', 'Bianchi',
]

export const CITIES = [
  'San Francisco, CA', 'New York, NY', 'London, UK', 'Berlin, Germany', 'Singapore',
  'Bangalore, India', 'Toronto, Canada', 'Amsterdam, Netherlands', 'Stockholm, Sweden',
  'Austin, TX', 'Seoul, South Korea', 'São Paulo, Brazil', 'Sydney, Australia', 'Dublin, Ireland',
]

/** City name only — for headlines where ", CA" would read as noise. */
export const CITY_SHORT = [
  'San Francisco', 'New York', 'London', 'Berlin', 'Singapore', 'Bangalore', 'Toronto',
  'Amsterdam', 'Stockholm', 'Austin', 'Seoul', 'São Paulo', 'Sydney', 'Dublin',
]

export const REGIONS = ['North America', 'EMEA', 'APAC', 'LATAM', 'Europe', 'India', 'Japan']

export const OUTLETS = [
  'Reuters', 'Bloomberg', 'Financial Times', 'The Wall Street Journal', 'TechCrunch',
  'Bloomberg Technology', 'The Information', 'CNBC', 'Business Insider', 'Fortune',
  'Nikkei Asia', 'The Economic Times', 'Mint', 'Rest of World', 'Axios', 'Sifted',
  'PitchBook News', 'The Register', 'Handshake', 'Korea Herald',
]

export const PEOPLE_TITLES: Record<PersonArchetype, string[]> = {
  founder: ['Founder & CEO', 'Co-founder & CTO', 'Founder, CEO and Chairman'],
  exec: ['Chief Executive Officer', 'Chief Financial Officer', 'Chief Technology Officer', 'Chief Operating Officer', 'Chief Marketing Officer'],
  investor: ['Partner at Meridian Capital', 'General Partner at Bluefield Ventures', 'Chair at Ridgeway Partners'],
  operator: ['VP Engineering', 'Head of Product', 'Director of Revenue Operations', 'Head of Corporate Development'],
  creator: ['Creator and CEO', 'Independent Researcher', 'Founder of an open-source project'],
  advisor: ['Independent Director', 'Operating Advisor', 'Board Chair'],
}

export const COMPANY_PRODUCT_NOUNS: Record<Archetype, string[]> = {
  saas: ['Flow', 'Relay', 'Atlas', 'Beacon', 'Signal', 'Orbit', 'Compass'],
  fintech: ['Ledger', 'Rail', 'Vault', 'Settle', 'Bridge', 'Clear'],
  ai: ['Copilot', 'Engine', 'Cortex', 'Pulse', 'Synth', 'Mirror'],
  ecommerce: ['Marketplace', 'Outlet', 'Storefront', 'Basket', 'Depot'],
  hardware: ['Drive', 'Rig', 'Module', 'Stack', 'Cell'],
  healthcare: ['Care', 'Clinic', 'Dose', 'Trial', 'Chart'],
  consumer: ['Kit', 'Pod', 'Daily', 'Habit', 'Bloom'],
  marketplace: ['Hub', 'Network', 'Exchange', 'Desk', 'Board'],
  devtools: ['SDK', 'Pipeline', 'Runtime', 'Forge', 'Stack'],
  energy: ['Grid', 'Cell', 'Array', 'Ramp', 'Loop'],
  media: ['Studio', 'Feed', 'Journal', 'Cast', 'Press'],
}

export const TOPIC_NOUNS = [
  'data residency', 'pricing', 'churn', 'latency', 'compliance', 'onboarding', 'retention',
  'unit economics', 'enterprise tier', 'developer tooling', 'international expansion',
  'vendor consolidation', 'AI safety review', 'hiring freeze', 'channel partnerships',
]

/**
 * Topics that actually make sense for a given category. Pairing a regulation
 * headline with "churn" produces nonsense, so each category draws from its own pool.
 */
/** Department nouns — used where a template says "head of {team}". */
export const TEAMS = [
  'Engineering', 'Product', 'Revenue', 'Operations', 'Infrastructure', 'Research',
  'Customer Success', 'Partnerships', 'Data', 'Security',
]

export const ACCOUNTING_DISPUTES = [
  'revenue recognition', 'capitalised software costs', 'customer prepayments',
  'related-party transactions', 'non-GAAP adjustments', 'goodwill impairment testing',
]

export const CATEGORY_TOPICS: Record<string, string[]> = {
  funding: ['dilution', 'runway', 'burn rate', 'down round terms', 'cap table', 'use of funds'],
  earnings: ['gross margin', 'ARR', 'operating margin', 'net revenue retention', 'bookings', 'the enterprise pipeline'],
  product: ['latency', 'developer tooling', 'model quality', 'onboarding', 'integrations', 'pricing'],
  partnerships: ['channel partnerships', 'reseller motion', 'co-selling', 'integration depth', 'joint go-to-market'],
  leadership: ['a succession plan', 'an org redesign', 'a hiring freeze', 'a shift in decision rights', 'a new operating cadence'],
  regulation: ['data residency', 'AI safety review', 'consumer protection', 'export controls', 'privacy rules'],
  litigation: ['intellectual property', 'employment claims', 'contract terms', 'antitrust exposure'],
  markets: ['the renewal rate', 'enterprise demand', 'the product roadmap', 'customer momentum', 'pipeline conversion'],
  customers: ['data migration', 'the enterprise tier', 'a multi-region rollout', 'the analytics suite', 'workflow automation', 'identity management'],
  expansion: ['international expansion', 'hiring plan', 'go-to-market coverage', 'localisation', 'new market entry'],
  acquisition: ['integration', 'dilution', 'the product roadmap', 'customer overlap', 'tal retention'],
  hiring: ['the hiring plan', 'the engineering bench', 'compensation bands', 'the leadership bench'],
  social: ['public positioning', 'the product roadmap', 'competitive positioning', 'industry narrative'],
  analysis: ['unit economics', 'the competitive moat', 'market structure', 'growth durability', 'the moat'],
}

/** Customer names — kept separate from investors and partners so a customer is
 *  never accidentally an investor. */
export const CUSTOMERS = [
  'Northgate Health', 'Bluefield Foods', 'Vireo Logistics', 'Halcyon Bank',
  'Tessellate Energy', 'Orbital Health', 'Peregrine Airlines', 'Calder Retail',
  'Westport Media', 'Nimbus Telecom', 'Ostrava Insurance', 'Quillon Labs',
]

export const INVESTORS = [
  'Meridian Capital', 'Bluefield Ventures', 'Ridgeway Partners', 'Northgate Fund',
  'Cobalt Row', 'Halcyon Partners', 'Verdant Growth', 'Arcline Capital',
]

export const REGIONS_SHORT = ['the US', 'the EU', 'India', 'Japan', 'Brazil', 'Canada', 'the UK', 'Southeast Asia']

export const MEDIA_TYPES = ['video', 'podcast', 'newsletter', 'essay', 'keynote', 'interview']

export const SURNAME_PARTICLES = ['the', 'a', 'an']
