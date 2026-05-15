#!/usr/bin/env python3
"""Extract structured data from docs/maps/*.md into data/*.json"""
import json, re, os, pathlib

MAPS_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = MAPS_DIR / "interactive" / "data"

UNITS = {
    "backend-config":     {"name": "Config",     "group": "BACKEND"},
    "backend-db":         {"name": "DB",         "group": "BACKEND"},
    "backend-evaluators": {"name": "Evaluators", "group": "BACKEND"},
    "backend-foundations":{"name": "Foundations","group": "BACKEND"},
    "backend-generators": {"name": "Generators", "group": "BACKEND"},
    "backend-integrations":{"name":"Integrations","group":"BACKEND"},
    "backend-main":       {"name": "Main",       "group": "BACKEND"},
    "backend-routes":     {"name": "Routes",     "group": "BACKEND"},
    "backend-scrapers":   {"name": "Scrapers",   "group": "BACKEND"},
    "backend-services":   {"name": "Services",   "group": "BACKEND"},
    "backend-tests":      {"name": "Tests",      "group": "BACKEND"},
    "frontend-components":{"name":"Components",  "group":"FRONTEND"},
    "frontend-core":      {"name": "Core",       "group": "FRONTEND"},
    "frontend-hooks":     {"name": "Hooks",      "group": "FRONTEND"},
    "frontend-settings":  {"name": "Settings",   "group": "FRONTEND"},
    "frontend-views":     {"name": "Views",      "group": "FRONTEND"},
    "build-ci":           {"name": "Build & CI", "group": "INFRA"},
    "tauri":              {"name": "Tauri",      "group": "INFRA"},
}

def parse_table(text):
    """Parse markdown table into list of dicts"""
    lines = text.strip().split("\n")
    if not lines:
        return []
    header_line = None
    sep_line = None
    data_lines = []
    for line in lines:
        if line.startswith("|") and not header_line:
            header_line = line
        elif line.startswith("|") and header_line and not sep_line:
            sep_line = line
        elif line.startswith("|") and sep_line:
            data_lines.append(line)
    if not header_line:
        return []
    headers = [h.strip() for h in header_line.strip("|").split("|")]
    results = []
    for dl in data_lines:
        cells = [c.strip() for c in dl.strip("|").split("|")]
        if len(cells) == len(headers):
            results.append(dict(zip(headers, cells)))
    return results

def flag_color(emoji):
    return {"🔴":"dead","🔵":"hardcoded","🟣":"coupled","⚪":"incomplete",
            "🟠":"stale","🟡":"suspect","🟢":"clean"}.get(emoji, "unknown")

def extract_flags(text):
    """Extract flag items from Flags summary section"""
    flags = []
    in_flags = False
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^##+\s+4\.\s*Flags\s+summary", stripped):
            in_flags = True
            continue
        if in_flags and re.match(r"^##+\s+5\.", stripped):
            in_flags = False
            continue
        if not in_flags:
            continue
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # P0/P1/P2/P3 | 🔴 DEAD | item | file:line | reason
            if len(cells) >= 5:
                prio = cells[0]
                flag_cell = cells[1]
                item = cells[2]
                location = cells[3]
                reason = cells[4]
                flag_type = None
                for e, t in [("🔴","dead"),("🔵","hardcoded"),("🟣","coupled"),
                             ("⚪","incomplete"),("🟠","stale"),("🟡","suspect"),("🟢","clean")]:
                    if e in flag_cell or e in flag_cell:
                        flag_type = t
                        break
                if flag_type:
                    flags.append({
                        "type": flag_type,
                        "item": item,
                        "location": location,
                        "reason": reason,
                        "priority": prio
                    })
    return flags

def extract_deps(text):
    """Extract dependency info"""
    inbound = []
    outbound = []
    current = None
    for line in text.split("\n"):
        if "**Inbound (other units depend on this):**" in line or "**Inbound" in line:
            current = "inbound"
            continue
        if "**Outbound (this unit depends on others):**" in line or "**Outbound" in line:
            current = "outbound"
            continue
        if current == "inbound" and line.strip():
            if line.strip().startswith("- "):
                inbound.append(line.strip()[2:].strip())
            elif line.strip().startswith("**") and "**" in line[2:]:
                current = None
        if current == "outbound" and line.strip():
            if line.strip().startswith("- "):
                outbound.append(line.strip()[2:].strip())
            elif line.strip().startswith("**") and "**" in line[2:]:
                current = None
    return inbound, outbound

def get_file_inventory(text):
    """Parse file inventory table"""
    m = re.search(r"##\s+2\.\s*File\s+inventory(.+?)(?=##\s+3\.)", text, re.DOTALL)
    if m:
        return parse_table(m.group(1))
    return []

def get_summary(text):
    """Get unit summary"""
    m = re.search(r"##\s+1\.\s*Unit\s+summary(.+?)(?=##\s+2\.)", text, re.DOTALL)
    if m:
        return m.group(1).strip().strip("|").strip()
    return ""

def get_assessment(text):
    """Get first principles assessment"""
    m = re.search(r"##\s+6\.\s*First\s+principles\s+assessment(.+)", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""

def extract_file_count(text):
    """Extract files count from header"""
    m = re.search(r"\*\*Files in scope:\*\*\s*(\d+)", text)
    return int(m.group(1)) if m else 0

def process_unit(slug):
    """Process a unit .md file into its JSON"""
    fpath = MAPS_DIR / f"{slug}.md"
    if not fpath.exists():
        return None
    text = fpath.read_text()
    info = UNITS.get(slug, {"name": slug.replace("backend-","").replace("frontend-","").replace("-"," ").title(), "group": "OTHER"})
    flags = extract_flags(text)
    inv = get_file_inventory(text)
    summary = get_summary(text)
    inbound, outbound = extract_deps(text)
    assessment = get_assessment(text)
    file_count = extract_file_count(text)
    flag_counts = {"dead":0,"hardcoded":0,"coupled":0,"incomplete":0,"stale":0,"suspect":0,"clean":0}
    for f in flags:
        if f["type"] in flag_counts:
            flag_counts[f["type"]] += 1
    return {
        "slug": slug,
        "name": info["name"],
        "group": info["group"],
        "summary": summary,
        "fileCount": file_count,
        "files": inv,
        "flags": flags,
        "flagCounts": flag_counts,
        "deps": {"inbound": inbound, "outbound": outbound},
        "assessment": assessment
    }

# Build overview.json (graph nodes + edges)
def build_overview():
    nodes = []
    edges = []
    all_flags = []
    total_flag_counts = {"dead":0,"hardcoded":0,"coupled":0,"incomplete":0,"stale":0,"suspect":0,"clean":0}
    for slug in UNITS:
        unit = process_unit(slug)
        if not unit:
            continue
        for ft, cnt in unit["flagCounts"].items():
            total_flag_counts[ft] += cnt
        all_flags.extend(unit["flags"])
        nodes.append({
            "id": slug,
            "name": unit["name"],
            "group": unit["group"],
            "fileCount": unit["fileCount"],
            "flagCounts": unit["flagCounts"],
            "summary": unit["summary"][:120]
        })
        for dep_line in unit["deps"]["inbound"]:
            m = re.search(r"`([^`]+)`", dep_line)
            if m:
                source = m.group(1).replace("/","-").replace(".","").replace("backend-","").replace("frontend-","")
                # Try to resolve to a known slug
    # Manual edges from INDEX.md and known deps
    edges = [
        {"source":"backend-config","target":"backend-db","label":"imports get_setting"},
        {"source":"backend-db","target":"backend-config","label":"imports settings"},
        {"source":"backend-main","target":"backend-config","label":"validate_all, settings"},
        {"source":"backend-main","target":"backend-foundations","label":"core.constants"},
        {"source":"backend-routes","target":"backend-db","label":"all routes import db.client"},
        {"source":"backend-routes","target":"backend-foundations","label":"schemas, ws_manager"},
        {"source":"backend-scrapers","target":"backend-evaluators","label":"lead_intel, quality_gate"},
        {"source":"backend-scrapers","target":"backend-main","label":"llm.call_llm"},
        {"source":"backend-services","target":"backend-scrapers","label":"orchestrates scouts"},
        {"source":"backend-services","target":"backend-evaluators","label":"evaluator.score"},
        {"source":"backend-evaluators","target":"backend-foundations","label":"logger"},
        {"source":"backend-generators","target":"backend-db","label":"data_base, get_profile"},
        {"source":"backend-generators","target":"backend-evaluators","label":"TECH_TAXONOMY"},
        {"source":"backend-integrations","target":"backend-main","label":"llm, config"},
        {"source":"backend-tests","target":"backend-db","label":"test db.client"},
        {"source":"frontend-core","target":"frontend-hooks","label":"useWS, useLeads"},
        {"source":"frontend-core","target":"frontend-components","label":"Sidebar, Topbar, etc"},
        {"source":"frontend-core","target":"frontend-views","label":"all views"},
        {"source":"frontend-core","target":"frontend-settings","label":"SettingsModal"},
        {"source":"build-ci","target":"backend-tests","label":"runs pytest"},
        {"source":"build-ci","target":"frontend-core","label":"builds frontend"},
        {"source":"tauri","target":"build-ci","label":"bundles via CI"},
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "flagCounts": total_flag_counts,
        "totalFlags": sum(total_flag_counts.values()),
        "totalFiles": sum(n["fileCount"] for n in nodes)
    }

# Build master-index.json
def build_master_index():
    entries = []
    for slug in UNITS:
        unit = process_unit(slug)
        if not unit:
            continue
        for f in unit["files"]:
            entries.append({
                "file": f.get("File",""),
                "unit": unit["name"],
                "unitSlug": slug,
                "lines": f.get("Lines",""),
                "purpose": f.get("Purpose",""),
                "flag": f.get("Overall flag",""),
            })
    return entries

# Build flags.json
def build_flags_registry():
    all_flags = []
    for slug in UNITS:
        unit = process_unit(slug)
        if not unit:
            continue
        for f in unit["flags"]:
            f["unit"] = unit["name"]
            f["unitSlug"] = slug
            all_flags.append(f)
    return all_flags

# Build flows.json
def build_flows():
    text = (MAPS_DIR / "flows.md").read_text()
    flows = []
    current_flow = None
    current_steps = []
    current_flags = []
    for line in text.split("\n"):
        m = re.match(r"^##\s+\d+\.\s+(.+?) Flow", line)
        if m:
            if current_flow:
                flows.append({"name": current_flow, "steps": current_steps, "flags": current_flags})
            current_flow = m.group(1).strip()
            current_steps = []
            current_flags = []
        if current_flow and "|" in line and "---" not in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 4 and cells[0].isdigit():
                current_steps.append({
                    "step": int(cells[0]),
                    "participant": cells[1],
                    "file": cells[2],
                    "action": cells[3]
                })
        flag_m = re.match(r"^\| (🔴|🔵|🟣|⚪|🟠|🟡|🟢)\s+(.+?)\s+\|\s+(.+?)\s+\|\s+(.+?)\s+\|", line)
        if flag_m and current_flow:
            current_flags.append({
                "type": flag_color(flag_m.group(1)),
                "item": flag_m.group(2).strip(),
                "source": flag_m.group(3).strip(),
                "reason": flag_m.group(4).strip()
            })
    if current_flow:
        flows.append({"name": current_flow, "steps": current_steps, "flags": current_flags})
    return flows

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Build and write overview
    overview = build_overview()
    (DATA_DIR / "overview.json").write_text(json.dumps(overview, indent=2))
    print(f"overview.json: {len(overview['nodes'])} nodes, {len(overview['edges'])} edges")
    
    # Build and write master-index
    master = build_master_index()
    (DATA_DIR / "master-index.json").write_text(json.dumps(master, indent=2))
    print(f"master-index.json: {len(master)} entries")
    
    # Build and write flags
    flags = build_flags_registry()
    (DATA_DIR / "flags.json").write_text(json.dumps(flags, indent=2))
    print(f"flags.json: {len(flags)} flags")
    
    # Build and write flows
    flows = build_flows()
    (DATA_DIR / "flows.json").write_text(json.dumps(flows, indent=2))
    print(f"flows.json: {len(flows)} flows")
    
    # Build and write unit JSONs
    for slug in UNITS:
        unit = process_unit(slug)
        if unit:
            fname = f"{slug.replace('backend-','').replace('frontend-','').replace('build-ci','build-ci').replace('tauri','tauri')}.json"
            (DATA_DIR / f"{slug}.json").write_text(json.dumps(unit, indent=2))
            print(f"{slug}.json: {unit['flagCounts']}")
    
    print("\nAll data files written.")

if __name__ == "__main__":
    main()
