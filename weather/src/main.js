import './assets/main.css'
// Bootstrap CSS (via npm install bootstrap) — falls back to CDN if missing
try {
	import('bootstrap/dist/css/bootstrap.min.css')
} catch (e) {
	// if dynamic import fails in some environments, it's non-fatal
}

import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
