# Cluster failure patterns — extracted from S1 debug_raw (FINAL_DISTRIBUTION, arm G)

## Trigger summary (auto-detected)

- **hint_text_budget=minimal_labels_only**: 9
- **prompt_mentions_3d**: 2
- **prompt_mentions_scan_like_wording(ct/mri/overlay)**: 4
- **style_mismatch(infographic_style!=visual_type_category)**: 1

## Extracted cluster payloads (exact)

### grp_a8b30bdbb7 / cluster_1

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `prompt_mentions_scan_like_wording(ct/mri/overlay), hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
Axial CT scan diagram of the temporal bone at the level of the epitympanum. Highlight the 'ice cream cone' appearance of the malleus head and incus body. Show the mastoid air cells posteriorly and the cochlea medially. Label the scutum (lateral epitympanic wall). Clean, medical textbook style line drawing overlaid on CT density background.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "forbidden_structures": [
      "Brain parenchyma details",
      "Eyeballs"
    ],
    "key_landmarks_to_include": [
      "Malleus head",
      "Incus body",
      "Mastoid air cells",
      "Scutum"
    ],
    "laterality": "Right",
    "organ": "Temporal Bone",
    "organ_system": "Musculoskeletal",
    "orientation": {
      "projection": "NA",
      "view_plane": "axial"
    },
    "subregion": "Middle Ear / Epitympanum"
  },
  "rendering_policy": {
    "forbidden_styles": [
      "photorealistic",
      "3D_volume_rendering"
    ],
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  }
}
```

### grp_a8b30bdbb7 / cluster_2

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `prompt_mentions_scan_like_wording(ct/mri/overlay), hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
Schematic of the Internal Auditory Canal (IAC) nerves in sagittal oblique view. Display four distinct nerve cross-sections: Facial nerve (anterior-superior), Cochlear nerve (anterior-inferior), Superior Vestibular nerve (posterior-superior), and Inferior Vestibular nerve (posterior-inferior). Use distinct colors or labels. Optionally include a side panel showing a sagittal TMJ MRI with a bow-tie shaped disc.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "key_landmarks_to_include": [
      "Facial nerve",
      "Cochlear nerve",
      "Superior Vestibular nerve",
      "Inferior Vestibular nerve"
    ],
    "laterality": "Right",
    "organ": "Cranial Nerves",
    "organ_system": "Nervous",
    "orientation": {
      "projection": "oblique",
      "view_plane": "sagittal"
    },
    "subregion": "Internal Auditory Canal",
    "topology_constraints": [
      "Facial nerve is anterior-superior",
      "Cochlear nerve is anterior-inferior"
    ]
  },
  "rendering_policy": {
    "style_target": "schematic_diagram",
    "text_budget": "minimal_labels_only"
  }
}
```

### grp_a8b30bdbb7 / cluster_3

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `prompt_mentions_3d, hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
3D bone reconstruction of the facial skeleton. Highlight the major buttresses: Zygomaticomaxillary complex, orbital rims, and mandible. Indicate the location of the Pterygopalatine fossa deep to the zygomatic arch. Color-code the zygoma, maxilla, and mandible distinctively to show sutures.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "key_landmarks_to_include": [
      "Zygoma",
      "Maxilla",
      "Mandible",
      "Orbit"
    ],
    "laterality": "Midline",
    "organ": "Skull",
    "organ_system": "Skeletal",
    "orientation": {
      "projection": "AP_oblique",
      "view_plane": "NA"
    },
    "subregion": "Facial bones"
  },
  "rendering_policy": {
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  }
}
```

### grp_47059b1c5d / cluster_1

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
Axial schematic diagram of the liver demonstrating the Couinaud classification segments (1 through 8). The image should clearly delineate the boundaries formed by the hepatic veins and portal vein plane. Label segments 1 (caudate), 2/3 (left lateral), 4 (left medial), 5/8 (right anterior), and 6/7 (right posterior) with distinct color coding.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "adjacency_rules": [
      "Caudate adjacent_to IVC",
      "Segment 4 adjacent_to Gallbladder"
    ],
    "forbidden_structures": [],
    "key_landmarks_to_include": [
      "IVC",
      "Gallbladder",
      "Ligamentum venosum",
      "Hepatic veins"
    ],
    "laterality": "Right",
    "organ": "Liver",
    "organ_system": "Gastrointestinal",
    "orientation": {
      "projection": "NA",
      "view_plane": "axial"
    },
    "subregion": "Segments 1-8",
    "topology_constraints": [
      "Hepatic veins divide sectors",
      "Portal vein divides superior/inferior"
    ]
  },
  "rendering_policy": {
    "forbidden_styles": [
      "photorealistic",
      "complex_3d_render"
    ],
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  },
  "safety": {
    "fallback_mode": "generic_conservative_diagram",
    "requires_human_review": false
  }
}
```

### grp_47059b1c5d / cluster_2

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `prompt_mentions_3d, hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
Coronal or transparent 3D view of the liver vasculature focusing on the three main hepatic veins (Right, Middle, Left) draining into the IVC superiorly, and the Portal Vein branching inferiorly. Highlight how these vessels serve as boundaries for the liver sectors (Right, Left, Anterior, Posterior).
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "adjacency_rules": [
      "Hepatic veins connect_to IVC",
      "Portal vein enters_at Porta Hepatis"
    ],
    "forbidden_structures": [
      "Stomach",
      "Colon"
    ],
    "key_landmarks_to_include": [
      "IVC",
      "Right Hepatic Vein",
      "Middle Hepatic Vein",
      "Left Hepatic Vein",
      "Main Portal Vein"
    ],
    "laterality": "NA",
    "organ": "Liver",
    "organ_system": "Gastrointestinal",
    "orientation": {
      "projection": "AP",
      "view_plane": "coronal"
    },
    "subregion": "Vasculature",
    "topology_constraints": []
  },
  "rendering_policy": {
    "forbidden_styles": [
      "photorealistic"
    ],
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  },
  "safety": {
    "fallback_mode": "generic_conservative_diagram",
    "requires_human_review": false
  }
}
```

### grp_47059b1c5d / cluster_3

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Physiology_Process`
- **triggers**: `prompt_mentions_scan_like_wording(ct/mri/overlay), hint_text_budget=minimal_labels_only, style_mismatch(infographic_style!=visual_type_category)`

**infographic_prompt_en (exact)**

```
Composite educational panel. Top row: Comparison of normal liver appearance on CT (homogeneous gray), MRI (T1 iso/hyper to spleen), and US (isoechoic to kidney). Bottom row: Typical spectral Doppler waveforms including Triphasic Hepatic Vein (A, S, D waves), Monophasic continuous Portal Vein, and Low-resistance Hepatic Artery.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "adjacency_rules": [],
    "forbidden_structures": [],
    "key_landmarks_to_include": [
      "Liver parenchyma",
      "Spleen (for comparison)",
      "Right Kidney (for comparison)"
    ],
    "laterality": "NA",
    "organ": "Liver",
    "organ_system": "Gastrointestinal",
    "orientation": {
      "projection": "NA",
      "view_plane": "NA"
    },
    "subregion": "Parenchyma and Vessels",
    "topology_constraints": []
  },
  "rendering_policy": {
    "forbidden_styles": [
      "photorealistic"
    ],
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  },
  "safety": {
    "fallback_mode": "generic_conservative_diagram",
    "requires_human_review": false
  }
}
```

### grp_ebdc9f5c1e / cluster_1

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `prompt_mentions_scan_like_wording(ct/mri/overlay), hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
A detailed sagittal cross-section medical illustration of the female pelvis focusing on the uterus. Clearly depict the three layers: high-signal endometrium, low-signal junctional zone, and intermediate myometrium. Show the cervix with its stromal ring. Include the rectouterine pouch (Pouch of Douglas) and indicate the position of the broad and round ligaments schematically. The style should mimic a T2-weighted MRI appearance converted to a clean diagram.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "adjacency_rules": [
      "Uterus anterior_to Rectum",
      "Uterus posterior_to Bladder"
    ],
    "forbidden_structures": [
      "Fetus",
      "Large tumors"
    ],
    "key_landmarks_to_include": [
      "Endometrium",
      "Junctional Zone",
      "Myometrium",
      "Cervix",
      "Rectouterine pouch"
    ],
    "laterality": "Midline",
    "organ": "Uterus",
    "organ_system": "Reproductive",
    "orientation": {
      "projection": "lateral",
      "view_plane": "sagittal"
    },
    "subregion": "Pelvis"
  },
  "rendering_policy": {
    "forbidden_styles": [
      "photorealistic",
      "3D_render"
    ],
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  },
  "safety": {
    "fallback_mode": "generic_conservative_diagram",
    "requires_human_review": false
  }
}
```

### grp_ebdc9f5c1e / cluster_2

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
A comparative medical illustration showing the ovarian cycle phases. Panel A: Early follicular phase with multiple small follicles in the cortex. Panel B: Mature Graafian follicle. Panel C: Corpus luteum with a thick, vascular wall ('ring of fire' appearance). The style should resemble a schematic ultrasound representation with clear anatomical labels for cortex, medulla, and follicles.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "forbidden_structures": [
      "Uterus (detailed)",
      "Fetus"
    ],
    "key_landmarks_to_include": [
      "Follicles",
      "Corpus Luteum",
      "Ovarian Stroma"
    ],
    "laterality": "L/R",
    "organ": "Ovary",
    "organ_system": "Reproductive",
    "orientation": {
      "projection": "AP",
      "view_plane": "coronal"
    },
    "subregion": "Adnexa"
  },
  "rendering_policy": {
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  },
  "safety": {
    "requires_human_review": false
  }
}
```

### grp_ebdc9f5c1e / cluster_3

- **visual_type_category**: `Anatomy_Map`
- **infographic_style**: `Anatomy_Map`
- **triggers**: `hint_text_budget=minimal_labels_only`

**infographic_prompt_en (exact)**

```
A medical diagram illustrating early pregnancy findings on ultrasound. Show a Gestational Sac (GS) eccentrically located within the thickened endometrium. Depict the 'Double Decidual Sign' with two concentric echogenic rings. Inside the GS, show a distinct Yolk Sac and a small Embryo pole. Include a separate inset showing normal placental attachment with a clear retroplacental space.
```

**infographic_hint_v2 (exact)**

```json
{
  "anatomy": {
    "adjacency_rules": [
      "Gestational_Sac inside Endometrium"
    ],
    "forbidden_structures": [
      "Large Fetus (late stage)",
      "Fibroids"
    ],
    "key_landmarks_to_include": [
      "Gestational Sac",
      "Yolk Sac",
      "Decidua",
      "Myometrium"
    ],
    "laterality": "Midline",
    "organ": "Uterus (Gravid)",
    "organ_system": "Reproductive",
    "orientation": {
      "projection": "lateral",
      "view_plane": "sagittal"
    },
    "subregion": "Endometrial cavity"
  },
  "rendering_policy": {
    "style_target": "flat_grayscale_diagram",
    "text_budget": "minimal_labels_only"
  },
  "safety": {
    "requires_human_review": false
  }
}
```
