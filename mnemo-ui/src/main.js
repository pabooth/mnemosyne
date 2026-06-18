import { createInitialState, createStore } from './state.js';
import { renderApp } from './render.js';

const root = document.querySelector('#app');
const store = createStore(createInitialState(), (state) => renderApp(root, store, state));

renderApp(root, store, store.getState());
