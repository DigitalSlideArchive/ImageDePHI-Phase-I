import client from './client';

export function getAssociatedLabels(itemId: string): Promise<Array<string>> {
  return client().get(`/api/v1/item/${itemId}/tiles/images`).json();
}
