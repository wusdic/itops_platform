import api from './request'

// Search
export const searchKnowledge = params => api.get('/knowledge/search', { params })

// SOP
export const getSopList = params => api.get('/knowledge/sop', { params })
export const createSop = data => api.post('/knowledge/sop', data)
export const getSop = id => api.get(`/knowledge/sop/${id}`)
export const updateSop = (id, data) => api.put(`/knowledge/sop/${id}`, data)
export const deleteSop = id => api.delete(`/knowledge/sop/${id}`)
export const submitSopReview = (id, data) => api.post(`/knowledge/sop/${id}/review`, data)
export const approveSop = id => api.post(`/knowledge/sop/${id}/approve`)

// Fault cases
export const getFaultCases = params => api.get('/knowledge/fault-case', { params })
export const createFaultCase = data => api.post('/knowledge/fault-case', data)
export const getFaultCase = id => api.get(`/knowledge/fault-case/${id}`)
export const updateFaultCase = (id, data) => api.put(`/knowledge/fault-case/${id}`, data)

// Categories & Tags
export const getCategories = () => api.get('/knowledge/category')
export const createCategory = data => api.post('/knowledge/category', data)
export const getTags = () => api.get('/knowledge/tag')

// Stats
export const getKnowledgeStats = () => api.get('/knowledge/stats')

// Review flows
export const getReviewFlows = params => api.get('/knowledge/review-flows', { params })
export const createReviewFlow = data => api.post('/knowledge/review-flows', data)
export const getReviewFlow = id => api.get(`/knowledge/review-flows/${id}`)
export const updateReviewFlow = (id, data) => api.put(`/knowledge/review-flows/${id}`, data)
export const deleteReviewFlow = id => api.delete(`/knowledge/review-flows/${id}`)

// Reviews
export const submitReview = data => api.post('/knowledge/reviews/submit', data)
export const getReviews = params => api.get('/knowledge/reviews', { params })
export const getPendingReviews = params => api.get('/knowledge/reviews/pending', { params })
export const approveReview = id => api.post(`/knowledge/reviews/${id}/approve`)
export const rejectReview = id => api.post(`/knowledge/reviews/${id}/reject`)
export const requestRevision = id => api.post(`/knowledge/reviews/${id}/request-revision`)
export const withdrawReview = id => api.post(`/knowledge/reviews/${id}/withdraw`)
export const resubmitReview = id => api.post(`/knowledge/reviews/${id}/resubmit`)
