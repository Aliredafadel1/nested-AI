const CHIPS = ["Generator hours?", "Water delivery?", "Safe area?", "Contract help?", "Internet providers?"]

export function QuickChips({ onSelect }: { onSelect: (text: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2 py-2">
      {CHIPS.map((chip) => (
        <button
          key={chip}
          onClick={() => onSelect(chip)}
          className="text-xs px-3 py-1.5 rounded-full border border-primary/30 text-primary hover:bg-primary/5 transition"
        >
          {chip}
        </button>
      ))}
    </div>
  )
}
