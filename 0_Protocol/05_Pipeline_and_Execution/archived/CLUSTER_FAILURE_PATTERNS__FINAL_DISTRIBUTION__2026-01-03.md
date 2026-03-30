# Cluster failure patterns — extracted from S1 debug_raw (FINAL_DISTRIBUTION, arm G)

Source artifacts:
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/debug_raw/stage1__group_grp_a8b30bdbb7__arm_G__raw_response.txt`
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/debug_raw/stage1__group_grp_47059b1c5d__arm_G__raw_response.txt`
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/debug_raw/stage1__group_grp_ebdc9f5c1e__arm_G__raw_response.txt`

## Executive summary (common triggers)

- **3D / reconstruction wording** shows up directly in cluster prompts and competes with S4’s “flat/2D schematic” safety+style rules.
  - Examples: “**3D bone reconstruction**…”, “**transparent 3D view**…”
- **Scan-background phrasing (CT scan / CT density background / overlaid)** pushes the model toward “scan-like” outputs that conflict with the intended “diagram, not a scan” contract.
  - Example: “**Axial CT scan diagram**… **overlaid on CT density background**.”
- **`rendering_policy.text_budget = minimal_labels_only`** appears consistently in cluster `infographic_hint_v2`, structurally discouraging the richer “Explanation / Key takeaways” text sections expected by S4 table-visual templates.
- **Style mismatch** can occur at the cluster level: group is `visual_type_category=Anatomy_Map` but a cluster may be `infographic_style=Physiology_Process` (e.g., Doppler waveforms panel), risking template mismatch unless routed by cluster style.

## Extracted payloads (exact)

### grp_a8b30bdbb7 / cluster_1

- `infographic_style=Anatomy_Map`
- `infographic_prompt_en` (exact):

```text
Axial CT scan diagram of the temporal bone at the level of the epitympanum. Highlight the 'ice cream cone' appearance of the malleus head and incus body. Show the mastoid air cells posteriorly and the cochlea medially. Label the scutum (lateral epitympanic wall). Clean, medical textbook style line drawing overlaid on CT density background.
```

- `infographic_hint_v2.rendering_policy.text_budget` (exact): `minimal_labels_only`

### grp_a8b30bdbb7 / cluster_2

- `infographic_style=Anatomy_Map`
- `infographic_prompt_en` (exact):

```text
Schematic of the Internal Auditory Canal (IAC) nerves in sagittal oblique view. Display four distinct nerve cross-sections: Facial nerve (anterior-superior), Cochlear nerve (anterior-inferior), Superior Vestibular nerve (posterior-superior), and Inferior Vestibular nerve (posterior-inferior). Use distinct colors or labels. Optionally include a side panel showing a sagittal TMJ MRI with a bow-tie shaped disc.
```

- `infographic_hint_v2.rendering_policy.text_budget` (exact): `minimal_labels_only`

### grp_a8b30bdbb7 / cluster_3

- `infographic_style=Anatomy_Map`
- `infographic_prompt_en` (exact):

```text
3D bone reconstruction of the facial skeleton. Highlight the major buttresses: Zygomaticomaxillary complex, orbital rims, and mandible. Indicate the location of the Pterygopalatine fossa deep to the zygomatic arch. Color-code the zygoma, maxilla, and mandible distinctively to show sutures.
```

- `infographic_hint_v2.rendering_policy.text_budget` (exact): `minimal_labels_only`

### grp_47059b1c5d / cluster_2

- `infographic_style=Anatomy_Map`
- `infographic_prompt_en` (exact):

```text
Coronal or transparent 3D view of the liver vasculature focusing on the three main hepatic veins (Right, Middle, Left) draining into the IVC superiorly, and the Portal Vein branching inferiorly. Highlight how these vessels serve as boundaries for the liver sectors (Right, Left, Anterior, Posterior).
```

- `infographic_hint_v2.rendering_policy.text_budget` (exact): `minimal_labels_only`

### grp_47059b1c5d / cluster_3 (style mismatch)

- Group: `visual_type_category=Anatomy_Map`
- Cluster: `infographic_style=Physiology_Process`
- `infographic_prompt_en` (exact):

```text
Composite educational panel. Top row: Comparison of normal liver appearance on CT (homogeneous gray), MRI (T1 iso/hyper to spleen), and US (isoechoic to kidney). Bottom row: Typical spectral Doppler waveforms including Triphasic Hepatic Vein (A, S, D waves), Monophasic continuous Portal Vein, and Low-resistance Hepatic Artery.
```

- `infographic_hint_v2.rendering_policy.text_budget` (exact): `minimal_labels_only`

### grp_ebdc9f5c1e / cluster_1

- `infographic_style=Anatomy_Map`
- `infographic_prompt_en` (exact):

```text
A detailed sagittal cross-section medical illustration of the female pelvis focusing on the uterus. Clearly depict the three layers: high-signal endometrium, low-signal junctional zone, and intermediate myometrium. Show the cervix with its stromal ring. Include the rectouterine pouch (Pouch of Douglas) and indicate the position of the broad and round ligaments schematically. The style should mimic a T2-weighted MRI appearance converted to a clean diagram.
```

- `infographic_hint_v2.rendering_policy.text_budget` (exact): `minimal_labels_only`


