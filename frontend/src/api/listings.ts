import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiJson, apiFetch } from "./client"

export interface Listing {
  id: number; title: string; price: number; bedrooms: number
  neighbourhood_id: number; description?: string; status: string
  lat?: number | null; lng?: number | null; fraud_score?: number | null
  amenities?: Record<string, boolean> | null
  photos?: { minio_key: string; is_primary: boolean }[]
}

export interface ListingFilters {
  neighbourhood_id?: number; min_price?: number; max_price?: number; bedrooms?: number
}

function buildQuery(filters: ListingFilters) {
  const p = new URLSearchParams()
  if (filters.neighbourhood_id) p.set("neighbourhood_id", String(filters.neighbourhood_id))
  if (filters.min_price) p.set("min_price", String(filters.min_price))
  if (filters.max_price) p.set("max_price", String(filters.max_price))
  if (filters.bedrooms) p.set("bedrooms", String(filters.bedrooms))
  return p.toString() ? `?${p}` : ""
}

export function useListings(filters: ListingFilters = {}) {
  return useQuery({
    queryKey: ["listings", filters],
    queryFn: () => apiJson<Listing[]>(`/listings${buildQuery(filters)}`),
  })
}

export function useListing(id: number) {
  return useQuery({
    queryKey: ["listing", id],
    queryFn: () => apiJson<Listing>(`/listings/${id}`),
  })
}

export function useMyListings() {
  return useQuery({
    queryKey: ["my-listings"],
    queryFn: () => apiJson<Listing[]>("/listings"),
  })
}

export function useSavedListings() {
  return useQuery({
    queryKey: ["saved-listings"],
    queryFn: () => apiJson<Listing[]>("/listings/saved"),
  })
}

export function useListingStats(id: number) {
  return useQuery({
    queryKey: ["listing-stats", id],
    queryFn: () => apiJson<{ listing_id: number; saved_count: number }>(`/listings/${id}/stats`),
  })
}

export function useSaveListing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch(`/listings/${id}/save`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-listings"] }),
  })
}

export function useUnsaveListing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch(`/listings/${id}/save`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-listings"] }),
  })
}

export function useCreateListing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Listing>) =>
      apiJson<Listing>("/listings", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["listings"] }),
  })
}

export function useUpdateListing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Listing> }) =>
      apiJson<Listing>(`/listings/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["listings"] }),
  })
}

export function useDeleteListing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch(`/listings/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["listings"] }),
  })
}

export function useUploadPhoto() {
  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => {
      const fd = new FormData(); fd.append("file", file)
      return apiJson<{ url: string }>(`/listings/${id}/photos`, { method: "POST", body: fd })
    },
  })
}

// ── Comparison ────────────────────────────────────────────────────────────────

export interface CompareAreaInfo {
  name: string; electricity_hours: number | null; generator_cost: number | null
  internet: number | null; transport: number | null; safety: number | null
  student_vibe: number | null; livability_score: number; student_score: number
}

export interface ListingCompareItem { listing: Listing; area: CompareAreaInfo; true_monthly: number }
export interface ListingCompareOut { items: ListingCompareItem[] }

export function useCompareListings() {
  return useMutation({
    mutationFn: (listing_ids: number[]) =>
      apiJson<ListingCompareOut>("/listings/compare", {
        method: "POST",
        body: JSON.stringify({ listing_ids }),
      }),
  })
}
