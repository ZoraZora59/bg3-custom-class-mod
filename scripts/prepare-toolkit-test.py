"""Port the local smoke-test data into the independently created Toolkit project.

Run with the editor closed. Field definitions come from installed official tables.
Multiclass can be included explicitly, using the verified SharedDev schema.
"""
from pathlib import Path
import argparse
import shutil
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument("--data", type=Path, required=True)
parser.add_argument("--folder", required=True)
parser.add_argument("--include-multiclass", action="store_true")
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
source = repo / "mods/SkeletonSmokeTest/Source"
folder = args.folder
if not folder.startswith("SkeletonToolkitTest_"):
    raise SystemExit("Expected the separately created SkeletonToolkitTest project")
meta = args.data / "Mods" / folder / "meta.lsx"
if not meta.is_file():
    raise SystemExit("Create the project in Toolkit first")
dest_editor = args.data / "Editor/Mods" / folder
snapshot = repo / "mods/SkeletonToolkitTest/Source"
for rel in ["ClassDescriptions/ClassDescriptions", "Progressions/Progressions", "Lists/SkillLists", "Lists/AbilityLists"]:
    reference = ET.parse(args.data / "Editor/Mods/Shared" / (rel + ".tbl")).getroot()
    definitions = {}
    for field in reference.iter("field"):
        definitions.setdefault(field.get("name"), dict(field.attrib))
    extra_reference = args.data / "Editor/Mods/SharedDev" / (rel + ".tbl")
    if extra_reference.is_file():
        for field in ET.parse(extra_reference).getroot().iter("field"):
            definitions.setdefault(field.get("name"), dict(field.attrib))
    output = ET.Element("stats", stat_object_definition_id=reference.get("stat_object_definition_id"))
    rows = ET.SubElement(output, "stat_objects")
    root = ET.parse(source / "Public/SkeletonSmokeTest" / (rel + ".lsx")).getroot()
    objects = root.findall("./region/node/children/node")
    for index, obj in enumerate(objects):
        attributes = {a.get("id"): dict(a.attrib) for a in obj.findall("attribute")}
        if attributes.get("IsMulticlass", {}).get("value") == "true" and not args.include_multiclass:
            continue
        fields = ET.SubElement(ET.SubElement(rows, "stat_object", is_substat="false"), "fields")
        ET.SubElement(fields, "field", name="Name", type="NameTableFieldDefinition", value=f"SkeletonToolkitTest_{rel.split('/')[-1]}_{index}")
        for name, attr in attributes.items():
            if name == "Comment":
                continue
            mapped = {"Name": "NameFS", "ParentGuid": "ParentUUID"}.get(name, name) if rel.startswith("ClassDescriptions") else ("FSName" if name == "Name" else name)
            definition = definitions.get(mapped)
            if definition is None:
                raise ValueError(f"Unknown official field: {rel}:{mapped}")
            new = {k: v for k, v in definition.items() if k not in {"value", "handle", "version"}}
            for k in ("value", "handle", "version"):
                if k in attr:
                    new[k] = attr[k].replace("SkeletonSmokeTest", "SkeletonToolkitTest")
            if attr.get("type") == "bool":
                new["value"] = new["value"].title()
            ET.SubElement(fields, "field", **new)
        subclasses = [a.get("value") for a in obj.findall("./children/node[@id='SubClasses']/children/node/attribute[@id='Object']")]
        if subclasses:
            ET.SubElement(fields, "field", name="SubClasses", type="GuidObjectListTableFieldDefinition", value=";".join(subclasses))
    ET.indent(output)
    target = dest_editor / (rel + ".tbl")
    target.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(output).write(target, encoding="utf-8", xml_declaration=True)
    snapshot_path = snapshot / "Editor/Mods" / folder / (rel + ".tbl")
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, snapshot_path)
    print(f"{rel}: {len(rows)} rows")
for relative in ["Public/SkeletonSmokeTest/Stats/Generated/Equipment.txt", "Public/SkeletonSmokeTest/Stats/Generated/Data/Passive.txt", "Mods/SkeletonSmokeTest/Localization/English/SkeletonSmokeTest.xml", "Mods/SkeletonSmokeTest/Localization/Chinese/SkeletonSmokeTest.xml"]:
    target_relative = relative.replace("SkeletonSmokeTest", folder, 1).replace("SkeletonSmokeTest.xml", "SkeletonToolkitTest.xml")
    text = (source / relative).read_text(encoding="utf-8-sig").replace("SkeletonSmokeTest", "SkeletonToolkitTest")
    for base in [args.data, snapshot]:
        target = base / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
for part in ["Mods", "Projects"]:
    target = snapshot / part / folder / "meta.lsx"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.data / part / folder / "meta.lsx", target)
print("Prepared source only; Toolkit must load, save, and export it.")
