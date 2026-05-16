<template>
  <div class="math-block">
    <div class="math-label">Statistical Analysis</div>
    <div class="math-content">
      <div class="math-formula" v-html="renderedFormula"></div>
      <div class="math-substitution" v-if="substitution" v-html="renderedSubstitution"></div>
      <div class="math-result">
        <span class="result-label">Result:</span>
        <span class="result-value">{{ result }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps(['content'])

const parsed = computed(() => {
  // The AI is told to show: Formula, Substitution, Result
  // Example: "Average = Σx/n | Σ(22,24,21)/3 = 67/3 | Result: 22.33"
  const parts = props.content.split('|').map(p => p.trim())
  return {
    formula: parts[0] || props.content,
    substitution: parts[1] || null,
    result: parts[2] || 'Calculated'
  }
})

const renderedFormula = computed(() => renderLatex(parsed.value.formula))
const renderedSubstitution = computed(() => renderLatex(parsed.value.substitution))

function renderLatex(text) {
  if (!text) return ''
  return text
    .replace(/\$\$(.+?)\$\$/gs, '<code class="latex-block">$1</code>')
    .replace(/\$([^$\n]+?)\$/g, '<code class="latex-inline">$1</code>')
}
</script>

<style scoped>
.math-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.math-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: #8b5cf6;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.math-content {
  background: rgba(139, 92, 246, 0.05);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(139, 92, 246, 0.2);
}
.math-formula {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  color: #c4b5fd;
  margin-bottom: 8px;
}
.math-substitution {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: #a5b4fc;
  margin-bottom: 12px;
  padding-left: 12px;
  border-left: 2px solid rgba(139, 92, 246, 0.3);
}
.math-result {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #fff;
}
.result-label {
  font-size: 0.8rem;
  color: #7a94b0;
}
.result-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  color: #8b5cf6;
}

:deep(.latex-block) {
  display: block;
  padding: 8px;
  background: rgba(0,0,0,0.3);
  border-radius: 6px;
  margin: 8px 0;
}
:deep(.latex-inline) {
  background: rgba(139, 92, 246, 0.2);
  padding: 2px 4px;
  border-radius: 4px;
}
</style>
