import type { Ref, DeepReadonly } from 'vue';
import { readonly, ref } from 'vue';

type ItemValue = {
  readonly id: string;
  readonly ifd: string;
  readonly subifd: string;
};
export type Item = Ref<ItemValue>;
