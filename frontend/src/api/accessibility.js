import { http } from './client.js';

const RESOURCE = '/accessibility-inspections';

export const accessibilityApi = {
  list: (params) => http.get(RESOURCE, params),
  summary: () => http.get(`${RESOURCE}/summary`),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id) => http.delete(`${RESOURCE}/${id}`),
};
