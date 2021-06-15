import ky from 'ky';
import type { GirderKeyspace, TileMetadata } from 'src/types';

class Endpoint<T> {
  route: string;

  constructor(route: string) {
    this.route = `/api/v1/${route}`;
  }

  fetch(): Promise<T> {
    return ky.get(this.route).json();
  }

  put(json: T) {
    return ky.put(this.route, { json });
  }
}

export default {
  geojson: (id: string) => new Endpoint<GirderKeyspace>(`item/${id}`),
  tileMetadata: (id: string) => new Endpoint<TileMetadata>(`item/${id}/tiles`),
  relatedImageURLs: (id: string) =>
    new Endpoint<Array<String>>(`item/${id}/tiles/images`),
  putgeojson: (id: string) =>
    new Endpoint<GirderKeyspace>(`item/${id}/metadata`),
};
