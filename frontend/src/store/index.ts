import { createStore, createLogger } from 'vuex';
import type { Store } from 'vuex';
import type { State as UserState } from './modules/user';
import user from './modules/user';

export interface State {
  user: UserState;
}

const store: Store<State> = createStore({
  modules: { user },
  strict: import.meta.env.DEV,
  plugins: import.meta.env.DEV ? [createLogger()] : [],
});

if (import.meta.hot) {
  import.meta.hot.accept(['./modules/user'], ([newUserModule]) => {
    store.hotUpdate({
      modules: {
        user: newUserModule,
      },
    });
  });
}

export default store;
