import type { FeatureCollection } from 'geojson';
import ky from 'ky';

class Endpoint<T> {
  route: string;

  constructor(route: string) {
    this.route = `/api/v1/${route}`;
  }

  fetch(): Promise<T> {
    return ky.get(this.route).json();
  }
}

export interface TileMetadata {
  levels: number;
  sizeX: number;
  sizeY: number;
  tileWidth: number;
  tileHeight: number;
}

export const api = {
  geojson: (id: string) => new Endpoint<FeatureCollection>(`item/${id}/tiles`),
  tileMetadata: (id: string) => new Endpoint<TileMetadata>(`item/${id}/tiles`),
};
