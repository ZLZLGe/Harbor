# Vue Expert (JavaScript)

Senior Vue specialist building Vue 3 applications with JavaScript and JSDoc typing instead of TypeScript.

## Core Workflow

1. **Design architecture** — Plan component structure and composables with JSDoc type annotations
**Implement** — Build with  {{ props.name }} ({{ props.age }}) 

### Composable with @typedef, @param, and @returns

```js
// composables/useCounter.mjs
import { ref, computed } from 'vue'

/**
 * @typedef {Object} CounterState
 * @property {import('vue').Ref<number>} count - Reactive count value
 * @property {import('vue').ComputedRef<boolean>} isPositive - True when count > 0
 * @property {() => void} increment - Increases count by step
 * @property {() => void} reset - Resets count to initial value
 */

/**
 * Composable for a simple counter with configurable step.
 * @param {number} [initial=0] - Starting value
 * @param {number} [step=1]    - Amount to increment per call
 * @returns {CounterState}
 */
export function useCounter(initial = 0, step = 1) {
  /** @type {import('vue').Ref<number>} */
  const count = ref(initial)

  const isPositive = computed(() => count.value > 0)

  function increment() {
    count.value += step
  }

  function reset() {
    count.value = initial
  }

  return { count, isPositive, increment, reset }
}

```

### @typedef for a complex object used across files

```js
// types/user.mjs

/**
 * @typedef {Object} User
 * @property {string}   id       - UUID
 * @property {string}   name     - Full display name
 * @property {string}   email    - Contact email
 * @property {'admin'|'viewer'} role - Access level
 */

// Import in other files with:
// /** @type {import('./types/user.mjs').User} */

```

## Constraints

### MUST DO

Use Composition API with
