import { Store } from 'vuex';
import type { State as UserState } from './store/modules/user';

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $store: {
      user: Store<UserState>;
    };
  }
}
