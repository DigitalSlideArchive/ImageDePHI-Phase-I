import type { Ref, DeepReadonly } from 'vue';
import { readonly, ref } from 'vue';

type UserValue = {
  readonly _id: string;
  readonly login: string;
  readonly admin: boolean;
};
export type User = Ref<UserValue>;
