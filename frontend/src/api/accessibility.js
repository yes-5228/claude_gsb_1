import { http } from './client.js';

const RESOURCE = '/accessibility-checks';

export const accessibilityApi = {
  list: (params) => http.get(RESOURCE, params),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  remove: (id) => http.delete(`${RESOURCE}/${id}`),
  summary: () => http.get(`${RESOURCE}/summary`),
};
