import client from './client';
import type { GirderKeyspace, TileMetadata } from '../types';

class Endpoint<T> {
  route: string;

  constructor(route: string) {
    this.route = `/api/v1/${route}`;
  }

  fetch(opt?: {}): Promise<T> {
    return client().get(this.route, opt).json();
  }

  put(json: T) {
    return client().put(this.route, { json });
  }
}

export default {
  geojson: (id: string) => new Endpoint<GirderKeyspace>(`item/${id}`),
  tileMetadata: (id: string) => new Endpoint<TileMetadata>(`item/${id}/tiles`),
  relatedImageURLs: (id: string) =>
    new Endpoint<Array<String>>(`item/${id}/tiles/images`),
  putgeojson: (id: string) =>
    new Endpoint<GirderKeyspace>(`item/${id}/metadata`),
  login: () => new Endpoint('user/authentication'),
};
