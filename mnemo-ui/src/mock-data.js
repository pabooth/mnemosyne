export function mockPreview(state) {
  return {
    title: 'Getting Started with PostgreSQL Full-Text Search',
    type: 'tutorial',
    sub_label: state.subLabel || 'postgresql',
    status: 'draft',
    tags: ['postgresql', 'full-text-search', 'tsvector', 'tsquery', 'gin-index'],
    summary: 'A step-by-step guide to implementing full-text search in PostgreSQL using tsvector and tsquery, covering GIN index configuration, query construction, and relevance ranking.',
    owner: state.owner || 'platform-team',
    last_reviewed: '2026-06-01',
    flags: ['Missing examples for multi-language configurations', 'Prerequisites section is incomplete'],
    body: `## Introduction

PostgreSQL's built-in full-text search offers a compelling alternative to dedicated search engines for many use cases. This guide walks through the core concepts and gets you to a working implementation.

## Prerequisites

- PostgreSQL 14 or later
- Basic familiarity with SQL DDL

## Step 1 - Add a search vector column

\`\`\`sql
ALTER TABLE documents
  ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))
  ) STORED;
\`\`\`

Using a generated column keeps the vector automatically in sync with your data.

## Step 2 - Create a GIN index

\`\`\`sql
CREATE INDEX idx_docs_fts
  ON documents
  USING GIN (search_vector);
\`\`\`

## Ranking functions

| Function | Behaviour |
|---|---|
| \`ts_rank\` | Frequency-based ranking |
| \`ts_rank_cd\` | Cover-density ranking |
`,
  };
}

export function mockIngest(state) {
  return {
    document: mockPreview(state),
    publish: {
      pr_url: 'https://github.com/org/knowledge-base/pull/247',
      branch: 'mnemo/getting-started-postgresql-fts-a3f8b2',
      file_path: 'kb/docs/tutorial/getting-started-postgresql-fts.md',
    },
  };
}
