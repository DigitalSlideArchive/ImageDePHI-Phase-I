import { ref, onMounted, watch, readonly } from 'vue';
import { api as bareapi } from '../api';

function getCookieToken() {
  const name = 'girderToken' + '=';
  const decodedCookie = decodeURIComponent(document.cookie);
  const ca = decodedCookie.split(';');
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return '';
}

export function useAuthentication() {
  const token = ref(getCookieToken());
  const user = ref('');

  const authenticate = async (login: string, password: string) => {
    const resp = await bareapi('/api/v1/user/authentication', {
      headers: {
        Authorization: 'Basic ' + btoa(login + ':' + password),
      },
      mode: 'cors',
    });
    const json = await resp.json();
    token.value = json.authToken.token;
    user.value = json.user.login;
  };

  const api = (url: string) => {
    return fetch(url, { headers: { 'Girder-Token': token.value } });
  };

  const checkAuthenticated = async () => {
    const resp = await api('/api/v1/user/me');
    const json = await resp.json();
    if (user.value !== json.login) {
      token.value = '';
      user.value = '';
    }
  };

  onMounted(checkAuthenticated);

  return {
    token,
    user,
    authenticate,
    checkAuthenticated,
    api,
  };
}
