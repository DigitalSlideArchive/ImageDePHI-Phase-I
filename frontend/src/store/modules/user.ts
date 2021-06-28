import type { Module } from 'vuex';
import { getLogin } from '../../api/user';

export interface State {
  authenticated: boolean | null;
  username: string | null;
}

const module = {
  namespaced: true,
  state: (): State => ({
    authenticated: false,
    username: null,
  }),
  mutations: {
    loginSuccess(state: State, username: string, token: string) {
      state.authenticated = true;
      state.username = username;
    },
  },
  actions: {
    async login({ commit }, { username, password }) {
      const userinfo = await getLogin(username, password);
      commit('loginSuccess', userinfo.login, userinfo.authToken.token);
    },
  },
  getters: {},
};

export default module;
