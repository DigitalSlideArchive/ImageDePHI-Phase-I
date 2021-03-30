import ky from 'ky';
import type { GeoJSON, TileMetadata } from 'src/types';

class Endpoint<T> {
  route: string;

  constructor(route: string) {
    this.route = `/api/v1/${route}`;
  }

  fetch(): Promise<T> {
    return ky.get(this.route).json();
  }
}

export default {
  geojson: (id: string) => new Endpoint<GeoJSON>(`item/${id}/tiles`),
  tileMetadata: (id: string) => new Endpoint<TileMetadata>(`item/${id}/tiles`),
};
