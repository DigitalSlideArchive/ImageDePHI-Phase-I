import ky from 'ky';

export interface User {
  authToken: {
    token: string;
    expires: Date;
  };
  admin: true;
  created: string;
  email: string;
  firstName: string;
  lastName: string;
  login: string;
}

export async function getLogin(
  username: string,
  password: string,
): Promise<User> {
  return await ky
    .get('/api/v1/user/authentication', {
      headers: {
        Authorization: `Basic ${btoa(username + ':' + password)}`,
      },
    })
    .json();
}
