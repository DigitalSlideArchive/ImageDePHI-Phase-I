import type { TileMetadata } from '../../api/models/TileMetadata';
import { ref, onMounted, watch } from 'vue';
import type { Ref } from 'vue';

export function useItemTileMetadata(
  itemid: Ref<string>,
  ifd: number,
  subifd: number,
) {
  const tileMetadata: Ref<TileMetadata | null> = ref(null);

  const getItemTileMetadata = async () => {
    const resp = await fetch(
      `/item/${itemid}/imagedephi/tile?ifd=${ifd}&subifd=${subifd}`,
    );
    tileMetadata.value = await resp.json();
  };

  onMounted(getItemTileMetadata);

  return {
    tileMetadata,
  };
}
