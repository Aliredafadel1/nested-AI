import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import L from "leaflet"
import markerIcon from "leaflet/dist/images/marker-icon.png"
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png"
import markerShadow from "leaflet/dist/images/marker-shadow.png"
import type { Listing } from "../../api/listings"

// Serve Leaflet marker icons from local bundle — avoids CDN fetches on every render
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

interface Props { listings: Listing[]; onPinClick: (id: number) => void }

export function ListingMap({ listings, onPinClick }: Props) {
  const withCoords = listings.filter((l) => l.lat && l.lng)
  return (
    <MapContainer
      center={[33.89, 35.50]}
      zoom={13}
      className="w-full h-full"
      style={{ minHeight: 400 }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {withCoords.map((l) => (
        <Marker
          key={l.id}
          position={[l.lat!, l.lng!]}
          eventHandlers={{ click: () => onPinClick(l.id) }}
        >
          <Popup>
            <strong>{l.title}</strong><br />${l.price}/mo
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
