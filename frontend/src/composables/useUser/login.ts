import { ref, onMounted, watch, readonly } from 'vue';

export function useLogin(login?: string, password?: string) {
  const token = ref('');

  const authenticate = async () => {
    if (!token.value && login && password) {
      const response = await fetch('/api/v1/user/me', {
        headers: { Authorization: btoa(`${login}:${password}`) },
      });
      const json = await response.json();
      token.value = json.authToken.token;
    }
  };

  const api = (url, options) => {
    fetch(url, { ...options, 'Girder-Token': token.value });
  };

  onMounted(authenticate);
  watch(token, authenticate);

  return {
    token,
    authenticate,
    api,
  };
}
