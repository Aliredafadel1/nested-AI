import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import L from "leaflet"
import type { Listing } from "../../api/listings"

// Fix Leaflet default icon path in Vite builds
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
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
