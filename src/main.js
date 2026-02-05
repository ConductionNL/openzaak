import Vue from 'vue'
import App from './App.vue'

Vue.mixin({ methods: { t, n } })

const appElement = document.getElementById('openzaak')
if (appElement) {
	new Vue({
		el: appElement,
		render: h => h(App),
	})
}
