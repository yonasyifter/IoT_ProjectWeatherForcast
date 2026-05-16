/**
 * agent-parser.js
 * Parses the AI's natural language response into structured insight blocks.
 */

export const BLOCK_TYPES = {
  TEXT: 'text',
  MATH: 'math',
  ANOMALY: 'anomaly',
  CHART: 'chart',
  CITATION: 'citation',
  GAP: 'gap'
}

export function parseAgentResponse(text) {
  if (!text) return []

  const blocks = []
  let remainingText = text

  // 1. Identify Knowledge Gaps (starts with "I don't have official data...")
  const gapPattern = /(I don't have official data for this, but based on general knowledge I can tell you that .*?)(?=\n\n|$)/gs
  let gapMatch
  while ((gapMatch = gapPattern.exec(remainingText)) !== null) {
    // We'll mark this for later insertion or handle it by splitting
    // For simplicity, let's use a splitting approach
  }

  // More robust approach: Split by double newlines and then categorize each segment
  const segments = text.split(/\n\n+/)

  for (const segment of segments) {
    const trimmed = segment.trim()
    if (!trimmed) continue

    // Check for Math Block ($$ ... $$)
    if (trimmed.includes('$$')) {
      blocks.push({ type: BLOCK_TYPES.MATH, content: trimmed })
      continue
    }

    // Check for Anomaly/Alert indicators (CRITICAL, WARNING, etc.)
    if (/CRITICAL|WARNING|ALERT|ANOMALY/i.test(trimmed) && (trimmed.includes('°C') || trimmed.includes('%') || trimmed.includes('dB'))) {
      blocks.push({ type: BLOCK_TYPES.ANOMALY, content: trimmed })
      continue
    }

    // Check for Knowledge Gaps
    if (trimmed.startsWith('I don\'t have official data for this')) {
      blocks.push({ type: BLOCK_TYPES.GAP, content: trimmed })
      continue
    }

    // Default to text
    blocks.push({ type: BLOCK_TYPES.TEXT, content: trimmed })
  }

  // Post-process to extract citations from text blocks
  return blocks.map(block => {
    if (block.type === BLOCK_TYPES.TEXT) {
      // We could split the text block into text and citation chips
      // For now, we'll keep it simple and just let the component handle the (Source: X) rendering
    }
    return block
  })
}

export function extractCitations(text) {
  const matches = [...text.matchAll(/\(Source:\s*([^)]+)\)/g)]
  return matches.map(m => m[1].trim())
}
