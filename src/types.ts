import type { FeatureCollection, Polygon } from 'geojson';

export interface TileMetadata {
  levels: number;
  sizeX: number;
  sizeY: number;
  tileWidth: number;
  tileHeight: number;
}

export interface GeoJSProperties {
  annotationType: 'polygon';
  name: string;
  description: string;
  annotationId: number;
  fill: boolean;
  fillColor: string;
  fillOpacity: number;
  stroke: boolean;
  strokeColor: string;
  strokeOpacity: number;
  strokeWidth: number;
}

export interface GeoJSON extends FeatureCollection<Polygon, GeoJSProperties> {}

export interface GirderKeyspace {
  imagedephi: {
    geojson: GeoJSON;
  };
}
