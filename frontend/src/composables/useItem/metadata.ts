import { ref, onMounted } from 'vue';
import type { Ref } from 'vue';

export function useItemMetadata(itemid: Ref<string>) {
  const metadata: string[][] = ref(null);

  const getItemMetadata = async () => {
    const resp = await fetch(`/api/v1/item/${itemid}/imagedephi/metadata`);
    metadata.value = await resp.json();
  };

  onMounted(getItemMetadata);

  return {
    metadata,
    getItemMetadata,
  };
}
