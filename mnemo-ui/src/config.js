export const DEFAULT_API_URL = 'http://localhost:7777';
export const API_TIMEOUT_MS = 30000;

export const CONTENT_TYPES = [
  { id: 'auto', label: 'Auto-detect', description: 'Let the pipeline decide' },
  { id: 'tutorial', label: 'Tutorial', description: 'Learning-oriented' },
  { id: 'how-to', label: 'How-to', description: 'Task-oriented' },
  { id: 'reference', label: 'Reference', description: 'Information-oriented' },
  { id: 'explanation', label: 'Explanation', description: 'Understanding-oriented' },
];

export const PREVIEW_STEPS = [
  'Classifying document',
  'Augmenting content',
  'Formatting',
];

export const INGEST_STEPS = [
  ...PREVIEW_STEPS,
  'Raising pull request',
];
