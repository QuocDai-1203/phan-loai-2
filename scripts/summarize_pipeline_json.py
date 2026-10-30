import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    d = json.load(f)

fr = d.get("file_routing", {})
print("=== TONG QUAN ===")
print("File:", d.get("file_name"))
print("Tong trang:", d.get("total_pages"))
print("Quyet dinh:", fr.get("decision"))
print("So lat cat:", fr.get("n_slices"))
print("Tu dong:", fr.get("n_auto"))
print("Can nguoi:", fr.get("n_needs_human"))

print()
print("=== PHAN LOAI ===")
for c in d.get("classifications", []):
    print("  Slice", c.get("slice_id"), ":", c.get("predicted_category"),
          "| tier=", c.get("tier"), "| conf=", c.get("confidence"))

print()
print("=== ROUTING ===")
for r in d.get("routing", []):
    print("  Slice", r.get("slice_id"), "->", r.get("decision"),
          "| category=", r.get("category"),
          "| reasons=", r.get("reasons"))

print()
print("=== CANH BAO ===")
for w in d.get("warnings", []):
    print(" -", w)

print()
print("=== THOI GIAN (ms) ===")
for k, v in d.get("stage_timings_ms", {}).items():
    print(" ", k, ":", v)
