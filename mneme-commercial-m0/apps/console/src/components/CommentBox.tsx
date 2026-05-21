// Small reusable comment box. SignOffButton inlines its own; this is for
// future reviewer-thread features in M1.

export function CommentBox({
  value,
  onChange,
  placeholder,
  rows = 3,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      className="w-full bg-mneme-bg border border-mneme-line text-mneme-text text-xs rounded px-2 py-1"
    />
  );
}
