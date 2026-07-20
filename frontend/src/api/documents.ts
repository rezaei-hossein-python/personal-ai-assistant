import { fetchFormData, fetchJson } from './http'
import type {
  DocumentResponse,
  DocumentSearchRequest,
  DocumentSearchResult,
} from './types'

export function uploadDocument(file: File, accessToken: string): Promise<DocumentResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return fetchFormData<DocumentResponse>('/documents/upload', formData, {
    method: 'POST',
    accessToken,
  })
}

export function listDocuments(accessToken: string): Promise<DocumentResponse[]> {
  return fetchJson<DocumentResponse[]>('/documents', {
    method: 'GET',
    accessToken,
  })
}

export function getDocument(documentId: number, accessToken: string): Promise<DocumentResponse> {
  return fetchJson<DocumentResponse>(`/documents/${documentId}`, {
    method: 'GET',
    accessToken,
  })
}

export function searchDocuments(
  request: DocumentSearchRequest,
  accessToken: string,
): Promise<DocumentSearchResult[]> {
  return fetchJson<DocumentSearchResult[]>('/documents/search', {
    method: 'POST',
    body: request,
    accessToken,
  })
}
