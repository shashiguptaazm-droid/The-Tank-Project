import Foundation

/// Authoritative Master Lore and Origin Stories for all 19 MBBS Subject Champions.
/// Strictly ported from Android `GuardianStories.kt`.
enum GuardianStories {

    static let stories: [Int: MasteryStory] = [
        // 1. AXIOM • ANATOMY
        1001: MasteryStory(
            avatarIndex: 1001,
            subjectTitle: "Anatomy (Gross, Neuro & Embryology)",
            chapterName: "Chapter I: The Architect of Ivory and Marrow",
            narrative: """
            Before he became the unbreakable Skeletal Guardian, Axiom was a humble student who spent four hundred sleepless nights in the cold granite dissection halls of the Old Medical College. While others memorized dry atlas drawings, Axiom traced every tributary of the internal jugular and untangled the tortuous roots of the brachial plexus with surgical reverence.

            During the Great Cranial Epidemic, surgeons were paralyzed by a complex skull-base variation that defied conventional textbooks. Standing beside the chief professor, Axiom calmly sketched the collateral microvascular arc of the foramen spinosum from memory, guiding the trephine blade with microscopic accuracy. He proved that human anatomy is not merely dead bone, but a living sacred blueprint where every groove, tubercle, and foramen guards a vital secret.

            From that dawn onward, he was crowned Master of Anatomy. Clad in ivory armor reinforced with glowing cerulean soulfire marrow, Axiom stands as the fortress against structural ignorance, ensuring no future clinician cuts blind.
            """,
            clinicalPhilosophy: "Structure dictates function; respect the fascia and the tissue will yield.",
            highYieldMnemonic: "Brachial Plexus Roots: 'Roots Drink Cold Beer' — Roots, Trunks, Divisions, Cords, Branches."
        ),

        // 2. PULSE • PHYSIOLOGY
        1002: MasteryStory(
            avatarIndex: 1002,
            subjectTitle: "Physiology & Cardiac Electrophysiology",
            chapterName: "Chapter II: The Symphony of the Sinus Node",
            narrative: """
            Pulse grew up in the shadow of the high-voltage telemetry unit, fascinated by the silent electrical choreography that keeps human blood moving. Where others saw squiggly ECG tracings, Pulse felt the ionic influx of sodium during Phase 0 depolarization and the delicate outward potassium flux maintaining resting membrane potentials.

            When a lightning strike overwhelmed the city substation and sent seventy coronary care patients into simultaneous ventricular tachyarrhythmias, backup power collapsed. Grasping twin manual defibrillator paddles and synchronizing his own bioelectric rhythm to the refractory period of the myocardium, Pulse delivered thirty-six successive timed countershocks at precisely the R-wave peak, restoring sinus rhythm without a single ischemic casualty.

            His body absorbed the residual electrical currents, transforming him into the Bioelectric Speedster. Today, his gauntlets crackle with rhythmic cardiac potentials, proving that understanding physiological equilibrium is the ultimate catalyst for human survival.
            """,
            clinicalPhilosophy: "Homeostasis is dynamic resistance; keep the gradient or face cellular collapse.",
            highYieldMnemonic: "Pacemaker Potential: Phase 4 'Funny' Na+ channels initiate spontaneous automaticity."
        ),

        // 3. CATALYST • BIOCHEMISTRY
        1003: MasteryStory(
            avatarIndex: 1003,
            subjectTitle: "Biochemistry & Molecular Genetics",
            chapterName: "Chapter III: The Alchemist of the Krebs Cycle",
            narrative: """
            In the dark subterranean chemical synthesis vaults, Catalyst sought the fundamental currency of life: adenosine triphosphate. While fellow scholars complained about the complexity of the citric acid cycle and glycolysis, Catalyst saw an ancient metabolic river flowing through every mitochondrial crista.

            During the catastrophic Cyanide Gas Leak at the industrial docks, casualties poured in with profound lactic acidosis and cytochrome c oxidase blockade. Standard protocols were failing. Catalyst rapidly improvised an intravenous cocktail combining sodium thiosulfate with an engineered methylene-blue electron bridge, bypassing the poisoned Complex IV and forcing mitochondrial ATP synthase to spin once more.

            The glowing purple distillation staff he wields carries the pure crystalline residue of that victory. As Master of Biochemistry, Catalyst commands enzymatic equilibrium, accelerating reactions and transmuting metabolic lethargy into overwhelming energy.
            """,
            clinicalPhilosophy: "Thermodynamics cannot be cheated, but enzymes can rewrite time itself.",
            highYieldMnemonic: "Krebs Cycle Steps: 'Citrate Is Krebs' Special Starting Substrate For Making Oxaloacetate'."
        ),

        // 4. NECROS • PATHOLOGY
        1004: MasteryStory(
            avatarIndex: 1004,
            subjectTitle: "Pathology & Histopathology",
            chapterName: "Chapter IV: The Gaze Beyond the Glass Slide",
            narrative: """
            Necros walked the forgotten corridors of the mortuary and surgical pathology archives. Where the world saw decay, he observed the cellular narrative: the transition from cloudy swelling to irreversible karyorrhexis, the chronic architecture of granulomas, and the malignant pleomorphism of undifferentiated neoplasms.

            When a mystifying hemorrhagic wasting syndrome afflicted the frontier garrison, clinicians were baffled by blood tests. Necros demanded a core needle liver biopsy. Staining the frozen section with emergency hematoxylin-eosin and silver methenamine in under four minutes, he identified intra-nuclear inclusion bodies diagnostic of a stealth viral cytopathy before organ failure could set in.

            Armed with his Biopsy Scythe, Necros cuts through pathological deception. He does not fear disease; he diagnoses it with clinical finality, dissolving diagnostic traps and revealing the microscopic truth written in human cells.
            """,
            clinicalPhilosophy: "The cell never lies under oil immersion; identify the etiology and cure will follow.",
            highYieldMnemonic: "Apoptosis vs Necrosis: Necrosis inflames and lyses; Apoptosis condenses and leaves no scar."
        ),

        // 5. PHARMA • PHARMACOLOGY
        1005: MasteryStory(
            avatarIndex: 1005,
            subjectTitle: "Pharmacology & Therapeutics",
            chapterName: "Chapter V: The Master of the Therapeutic Index",
            narrative: """
            Pharma lived by the timeless maxim of Paracelsus: all things are poison; only the dose makes the remedy. In her botanical and chemical laboratory, she memorized every receptor affinity curve, first-pass hepatic clearance rate, and cytochrome P450 competitive inhibition pathway known to medicine.

            Her crowning test came during the Great Organophosphate Poisoning Disaster, where eighty agricultural workers collapsed simultaneously in cholinergic crisis. While panic ensued, Pharma calculated the exact pralidoxime reactivator titrations and paired them with micro-dosed atropine sulfate infusions, reversing bronchial secretions and nicotinic muscle paralysis in record time without triggering atropine delirium.

            Crowned the Vanguard Chemist, Pharma wears tactical antidote syringes at her bandolier. She controls the exact molecular keys that bind cell receptors, turning fatal toxicology into lifesaving recovery.
            """,
            clinicalPhilosophy: "Receptor affinity without clinical vigilance is poison; titrate to effect.",
            highYieldMnemonic: "Cholinergic SLUDGE: Salivation, Lacrimation, Urination, Defecation, GI upset, Emesis."
        ),

        // 6. MICROX • MICROBIOLOGY
        1006: MasteryStory(
            avatarIndex: 1006,
            subjectTitle: "Microbiology & Infectious Diseases",
            chapterName: "Chapter VI: The Warden of the Sterile Zone",
            narrative: """
            Encased in his pressurized yellow containment suit, Microx spent decades inside Level 4 containment facilities. To him, bacteria, viruses, fungi, and parasites were not invisible wraiths, but cunning biological opponents with specific cell-wall peptidoglycans, flagellar antigens, and virulence plasmids.

            During the outbreak of a pan-resistant superbug in the central burn unit, standard broad-spectrum carbapenems failed completely. Microx collected wound swabs at 2 AM, performed rapid fluorescent-labeled antibody tests, and isolated a novel metallo-beta-lactamase producer. He deployed a targeted polymyxin-colistin synergistic envelope while constructing strict barrier laminar isolation, extinguishing the outbreak in three days.

            Microx carries the Petri Aegis and micro-pipette injector into the arena. He isolates pathogenic traps and immunizes students against microbiological deceit.
            """,
            clinicalPhilosophy: "A sterile field broken is a battle lost; identify the Gram stain first.",
            highYieldMnemonic: "Gram-Positive Cocci: Staph forms clusters like grapes; Strep forms chains like tracks."
        ),

        // 7. VERDICT • FORENSIC MEDICINE
        1007: MasteryStory(
            avatarIndex: 1007,
            subjectTitle: "Forensic Medicine & Toxicology (FMT)",
            chapterName: "Chapter VII: The Inquest of the Unspoken",
            narrative: """
            Verdict never accepts surface appearances. Wearing his leather detective duster and badge of jurisprudence, he investigated hundreds of unsolved mortuary enigmas across thirty provinces. To Verdict, contusions, lacerations, bullet stippling, and post-mortem lividity tell an unalterable forensic truth.

            In the famous High Minister Poisoning Inquest, three physicians declared the death a natural myocardial infarction. Verdict examined the conjunctivae, noted subtle subungual cyanosis, and excised the gastric mucosa, demonstrating the tell-tale garlic odor and mucosal petechiae of acute arsenic toxicity, accompanied by microscopic antemortem ligature furrows.

            Armed with his lighted magnifying monocle and inquest beam, Verdict reconstructs the exact timeline of injury. He cuts through clinical speculation and demands rigorous forensic certainty.
            """,
            clinicalPhilosophy: "The dead speak with absolute honesty to those trained to listen.",
            highYieldMnemonic: "Post-Mortem Changes: Algor (Cold), Livor (Color), Rigor (Stiffness)."
        ),

        // 8. CURA • COMMUNITY MEDICINE
        1008: MasteryStory(
            avatarIndex: 1008,
            subjectTitle: "Community Medicine & PSM",
            chapterName: "Chapter VIII: The Guardian of the Collective Sphere",
            narrative: """
            While other doctors waited inside hospital walls for patients to arrive, Cura walked the dusty roads of river deltas, tribal hamlets, and crowded slums. She understood that clean water, maternal immunization, cold-chain maintenance, and sanitation save a thousand times more lives than the sharpest scalpel.

            When a deadly waterborne cholera epidemic threatened to engulf a valley of forty thousand refugees, Cura mobilized the community before panic struck. She mapped the primary contagion vectors using John Snow spatial clustering, chlorinated every village well, established oral rehydration centers at crossroads, and deployed ring-vaccination teams with a 99.4% cold-chain success rate.

            Her Vaccine Tower Shield and Biosphere Orb symbolize public health mastery. Cura stands as the defender of the population, proving that prevention is the highest form of clinical medicine.
            """,
            clinicalPhilosophy: "Treat the individual and you save a life; treat the community and you save a generation.",
            highYieldMnemonic: "Epidemiological Triad: Agent, Host, Environment — break one leg to stop the disease."
        ),

        // 9. MEDICUS • GENERAL MEDICINE
        1009: MasteryStory(
            avatarIndex: 1009,
            subjectTitle: "General Medicine & Differential Diagnosis",
            chapterName: "Chapter IX: The Grand Diagnostician",
            narrative: """
            Medicus was known throughout the wards as the physician who could walk into a room, glance at a patient's fingertips, listen to their heartbeat for twenty seconds, and unravel a multi-system mystery that had baffled specialists for months. He possessed an encyclopedic synthesis of clinical semiology.

            During the mystery outbreak at the Royal Infirmary, a young patient presented with simultaneous delirium, petechial rash, renal failure, and high fever. Specialists argued between bacterial meningitis, malaria, and drug allergy. Medicus felt the splinter hemorrhages beneath the nails, auscultated the subtle changing murmur of aortic insufficiency, and diagnosed acute infective endocarditis with systemic septic embolization, initiating blood cultures and targeted therapy within sixty minutes.

            Bearing the Golden Caduceus and stethoscope mantle, Medicus represents the peak of bedside diagnosis. He unifies disparate laboratory values into a clear, decisive diagnostic path.
            """,
            clinicalPhilosophy: "Listen to the patient; they are telling you the diagnosis.",
            highYieldMnemonic: "Infective Endocarditis Duke Criteria: 'BE FEVER' — Bacteremia, Endocardial involvement, Fever, Vascular signs, Evident immunologic signs, Risk factors."
        ),

        // 10. SURGON • GENERAL SURGERY
        1010: MasteryStory(
            avatarIndex: 1010,
            subjectTitle: "General Surgery & Operating Theater",
            chapterName: "Chapter X: The Maestro of the Steel Scalpel",
            narrative: """
            In the sterile quiet of Operating Room 1, Surgon moved with the poise of an artist and the precision of a chronometer. He trained under battle surgeons, learning that true surgical mastery lies not in bold cutting, but in anatomical discipline, gentle tissue handling, and absolute hemostasis.

            During a multi-car pileup, an unstable polytrauma patient arrived in hypovolemic shock with a grade V liver laceration and mesenteric avulsion. With systemic pressure dropping through the floor, Surgon performed an emergency midline laparotomy in ninety seconds, executed a flawless Pringle maneuver to control hepatic inflow, and packed the retroperitoneum while repairing the torn mesenteric arcade without a drop of wasted blood.

            His Scalpel Sabre and Micro-Retractor are legendary across the surgical wards. Surgon cuts away pathology with millimeter accuracy, proving that a calm mind inside the abdomen saves the most desperate cases.
            """,
            clinicalPhilosophy: "A good surgeon knows how to operate; a better surgeon knows when to operate; the best knows when not to.",
            highYieldMnemonic: "Acute Abdomen Triage: 'Perforation, Obstruction, Ischemia, Inflammation' — rule out rupture first."
        ),

        // 11. VITA • OBGYN
        1011: MasteryStory(
            avatarIndex: 1011,
            subjectTitle: "Obstetrics & Gynecology (OBGYN)",
            chapterName: "Chapter XI: The Keeper of the First Breath",
            narrative: """
            Vita spent her life guarding the sacred threshold where new life enters the world. She understood the intricate dance between maternal circulation, placental gas exchange, and the delicate neuro-hormonal cascades that guide labor.

            In the midnight storm of the Century Flood, the labor ward lost power as a mother with severe pre-eclampsia developed sudden seizures and uterine rupture at 33 weeks. Operating under battery-powered headlamps, Vita stabilized the eclamptic crisis with magnesium sulfate, performed a rapid emergency cesarean section, extracted twin neonates safely, and repaired the uterine tear in twenty-eight minutes, saving all three lives.

            Her golden maternal coronet and fetal heart shield embody life-giving resilience. Vita protects learners from fatal clinical oversights and nurtures knowledge into clinical mastery.
            """,
            clinicalPhilosophy: "Two heartbeats in one body; never sacrifice the mother to save the child, never lose the child while saving the mother.",
            highYieldMnemonic: "PPH Management: 'Tone, Trauma, Tissue, Thrombin' — the 4 Ts of postpartum hemorrhage."
        ),

        // 12. PEDIA • PEDIATRICS
        1012: MasteryStory(
            avatarIndex: 1012,
            subjectTitle: "Pediatrics & Neonatology",
            chapterName: "Chapter XII: The Protector of the Fragile Flame",
            narrative: """
            Children are not small adults; their physiology, pharmacokinetics, and resilience operate on completely different rules. Pedia learned this fundamental truth in the neonatal intensive care nursery, where a change of five milliliters of fluid can mean the difference between life and death.

            When a severe respiratory syncytial virus epidemic hit the community crèches, hundreds of infants developed bronchiolitis and grunting tachypnea. Pedia organized rapid triage wards based on pulse oximetry and retraction scores. With gentle hands, he stabilized collapsed airways, calibrated humidified high-flow oxygen, and calculated weight-based fluid boluses without a single iatrogenic complication.

            Carrying his Growth-Chart Staff and Teddy Bear Aegis, Pedia radiates warmth and hope. He defends against rapid clinical deterioration and teaches that attentive tenderness is medicine's greatest ally.
            """,
            clinicalPhilosophy: "A child's smile on morning rounds is the only discharge summary that truly matters.",
            highYieldMnemonic: "APGAR Score at 1 & 5 mins: Appearance, Pulse, Grimace, Activity, Respiration."
        ),

        // 13. OSTEON • ORTHOPEDICS
        1013: MasteryStory(
            avatarIndex: 1013,
            subjectTitle: "Orthopedics & Joint Reconstruction",
            chapterName: "Chapter XIII: The Titan of the Biomechanical Forge",
            narrative: """
            Osteon viewed the human skeleton as an architectural triumph of living biomechanics, stress vectors, and compressive loads. In his orthopedic theater, bone drills, mallet chisels, and titanium compression plates were instruments of miraculous restoration.

            When an earthquake collapsed the regional railway viaduct, twelve construction workers suffered catastrophic compound pelvic fractures and comminuted femoral trauma. Working for eighteen continuous hours in hydraulic armor, Osteon reduced open fractures, positioned pelvic C-clamps to arrest internal hemorrhage, and locked intramedullary nails with sub-millimeter anatomical alignment, allowing all twelve workers to walk again within six months.

            Encased in titanium casts and wielding the Hydraulic Crutch Hammer, Osteon provides unbreakable structural reinforcement. He crushes doubt and locks score streaks in place.
            """,
            clinicalPhilosophy: "Align the axes, secure rigid fixation, and let the living osteoblasts do the rest.",
            highYieldMnemonic: "Open Fracture Gustilo Classification: Grade I (<1cm), Grade II (1-10cm), Grade III (>10cm or high energy)."
        ),

        // 14. OPTIX • OPHTHALMOLOGY
        1014: MasteryStory(
            avatarIndex: 1014,
            subjectTitle: "Ophthalmology & Retinal Optics",
            chapterName: "Chapter XIV: The Master of the Twenty-Twenty Lens",
            narrative: """
            To Optix, the human eye was the only window where living cranial nerves and blood vessels could be inspected directly without an incision. He spent decades studying anterior chamber fluid dynamics, corneal refraction, and the delicate neuro-retinal layers of the fovea centralis.

            During an industrial laser laboratory accident, three researchers suffered severe retinal tears threatening macula-off detachment. Optix set up his high-frequency argon laser slit-lamp apparatus in the emergency bay. With unshaking hands and microscopic precision, he applied four hundred barrier photocoagulation burns around the retinal breaks in under fifteen minutes, preserving complete central visual acuity.

            Armed with his Argon Sniper Scope and Slit-Lamp Gauntlets, Optix eliminates diagnostic illusions from afar, guiding students with 20/20 clarity through optical exam traps.
            """,
            clinicalPhilosophy: "Protect the macula at all costs; once photoreceptors degenerate, light is forever lost.",
            highYieldMnemonic: "Red Eye Differential: Conjunctivitis (painless, discharge), Keratitis (pain, photophobia), Glaucoma (halos, hard eye)."
        ),

        // 15. RESONA • ENT
        1015: MasteryStory(
            avatarIndex: 1015,
            subjectTitle: "Otorhinolaryngology (ENT)",
            chapterName: "Chapter XV: The Weaver of Sonic Harmonics",
            narrative: """
            Resona could hear the subtlest change in air currents passing through the nasopharynx, the minute vibratory damping of a sclerotic stapes footplate, and the diagnostic acoustic tones of a 512 Hz tuning fork. She mastered the complex anatomy of the temporal bone and cranial nerve pathways.

            In the tragic coal mine explosion, trapped miners suffered blast wave barotrauma. While others struggled in the dark, Resona used endoscopic micro-suction and pneumatic otoscopy to identify perilymphatic fistulas and bilateral vocal cord abductor paralysis, performing emergency awake cricothyroidotomies that prevented catastrophic asphyxiation.

            Bearing the Harmonic Tuning Staff and Otic Shield, Resona detects hidden frequency clues in clinical case vignettes, tuning out ambient exam confusion and revealing the correct answer.
            """,
            clinicalPhilosophy: "Listen to the tone of the breath; the airway is the threshold of life.",
            highYieldMnemonic: "Weber & Rinne Tests: Rinne AC > BC is normal; Weber lateralizes to diseased ear in conductive loss."
        ),

        // 16. DERMA • DERMATOLOGY
        1016: MasteryStory(
            avatarIndex: 1016,
            subjectTitle: "Dermatology & Venereology (DVL)",
            chapterName: "Chapter XVI: The Sentinel of the Stratified Barrier",
            narrative: """
            Derma knew that the skin is the body's largest immune organ and an open mirror reflecting internal medicine. Where untrained eyes saw identical red macules, Derma distinguished Wickham's striae, Auspitz's sign, targetoid lesions of erythema multiforme, and atypical pigment networks of early melanoma.

            A foreign diplomat arrived in the capital with an acute blistering disease that three private clinics diagnosed as simple allergic urticaria. Derma noticed Nikolsky's sign was positive and performed an immediate Tzanck smear and frozen-section punch biopsy, confirming Pemphigus Vulgaris before full-body desquamation and sepsis could ensue, saving the diplomat through high-dose systemic immunosuppression.

            Her Keratin Aegis glows with protective amber energy. Derma acts as the ultimate epidermal shield, deflecting penalties and preserving clinical skin integrity.
            """,
            clinicalPhilosophy: "Examine the nails, the mucosa, and the scalp; dermatological truth is in the margins.",
            highYieldMnemonic: "Melanoma ABCDE: Asymmetry, Border irregularity, Color variegation, Diameter >6mm, Evolution."
        ),

        // 17. SYNAPSE • PSYCHIATRY
        1017: MasteryStory(
            avatarIndex: 1017,
            subjectTitle: "Psychiatry & Behavioral Sciences",
            chapterName: "Chapter XVII: The Harmonizer of the Mind",
            narrative: """
            Synapse understood the invisible labyrinth of human consciousness, neurotransmitter pathways, and psychological defenses. While others dismissed psychiatric crises as non-organic, Synapse mapped the dysregulation of dopaminergic mesolimbic circuits and serotonin reuptake kinetics.

            During the city-wide Panic Blackout, hundreds of citizens developed acute delirium, conversion disorders, and catatonic stupors. Synapse entered the crowded emergency shelter, calmly conducted rapid mental status examinations, and differentiated neuroleptic malignant syndrome from acute panic through serum creatine kinase checks and gentle de-escalation psychotherapy, restoring emotional equilibrium without physical restraint.

            Surrounded by glowing purple psionic neural networks, Synapse soothes exam panic. He freezes anxiety in its tracks, giving students clear, calm mental space to solve the hardest vignettes.
            """,
            clinicalPhilosophy: "Never belittle emotional pain; the mind and the body heal on the same neurochemical altar.",
            highYieldMnemonic: "Depression SIG E CAPS: Sleep, Interest, Guilt, Energy, Concentration, Appetite, Psychomotor, Suicidal ideation."
        ),

        // 18. RAYNE • RADIODIAGNOSIS
        1018: MasteryStory(
            avatarIndex: 1018,
            subjectTitle: "Radiodiagnosis & Imaging",
            chapterName: "Chapter XVIII: The Seer of the Invisible Rays",
            narrative: """
            Rayne operated in the dim glow of multi-monitor PACS workstations. To her, X-rays, computerized tomography, magnetic resonance imaging, and Doppler ultrasound were clairvoyant windows penetrating solid bone and flesh with zero tactile resistance.

            When a young athlete was admitted with mild headache after a sporting tackle, physical exam was entirely normal. Rayne scrutinized the non-contrast head CT and noticed a subtle 1mm hyperdense middle cerebral artery sign and faint cortical sulcal effacement indicating hyperacute ischemic stroke within the 3-hour therapeutic window. Her immediate alert allowed thrombolytic therapy to dissolve the clot before permanent hemiplegia occurred.

            Her X-Ray Cape and CT photon scanners reveal hidden diagnostic truths through opaque question stems, illuminating the correct clinical pathway with radiologic certainty.
            """,
            clinicalPhilosophy: "A shadow is only meaningless until you understand where the light source lies.",
            highYieldMnemonic: "Chest X-Ray ABCDE: Airway, Breathing (lungs), Cardiac silhouette, Diaphragm, Everything else (bones, lines)."
        ),

        // 19. SOMNUS • ANESTHESIOLOGY
        1019: MasteryStory(
            avatarIndex: 1019,
            subjectTitle: "Anesthesiology & Critical Care",
            chapterName: "Chapter XIX: The Sentinel of the Twilight Threshold",
            narrative: """
            Somnus was the silent guardian standing at the head of the operating table. In his hands rested the power to render human beings completely insensible to agony, maintain their breathing on mechanical bellows, and guide them safely back across the threshold of consciousness.

            During an emergency triple-valve replacement surgery, the patient suffered an acute malignant hyperthermia crisis: end-tidal CO2 skyrocketed to 95, body temperature reached 106°F, and muscle rigidity seized the jaw. Working at lightning speed, Somnus halted all volatile anesthetic agents, hyperventilated with 100% chilled oxygen, and rapidly administered intravenous dantrolene sodium while packing iced saline, cooling the core and saving the patient from fatal rhabdomyolysis.

            Wearing his narcosis mask and vaporizer robes, Somnus commands the twilight zone of consciousness. He absorbs penalties, stabilizes unstable vital signs, and brings clarity to critical moments.
            """,
            clinicalPhilosophy: "Anesthesia is hours of peaceful vigilance punctuated by seconds of lifesaving reflex.",
            highYieldMnemonic: "Difficult Airway LEMON: Look externally, Evaluate 3-3-2 rule, Mallampati score, Obstruction, Neck mobility."
        )
    ]

    static func getStory(avatarIndex: Int) -> MasteryStory? {
        stories[avatarIndex]
    }
}
