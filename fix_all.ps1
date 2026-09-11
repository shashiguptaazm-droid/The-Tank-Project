Write-Host "=== Fixing thesis_workspace.php ===" -ForegroundColor Cyan

$path = 'C:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend\thesis_workspace.php'
$content = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
$original = $content
$changes = 0

# === FIX 1: Empty paragraphs bug ===
$content = $content -replace '(?<=        const paragraphs = )sec\.paragraphs \|\| \[sec\.content \|\| ""\]', '(sec.paragraphs && sec.paragraphs.length > 0) ? sec.paragraphs : [sec.content || ""]'
if ($content -ne $original) { Write-Host "  [FIX 1] Fixed empty paragraphs bug" -ForegroundColor Green; $changes++ } else { Write-Host "  [FIX 1] Not found" -ForegroundColor Yellow }

# === FIX 2: Add bullets/numbered_points/subsections rendering ===
$content = $content -replace '(?s)(      }\);\r?\n\s+\r?\n\s+// Actions)', @'

        // Render bullets if present
        if (sec.bullets && sec.bullets.length > 0) {
          const bulletList = document.createElement('ul');
          bulletList.className = 'section-bullet-list';
          bulletList.style.cssText = 'margin: 8px 0; padding-left: 24px; color: var(--text-secondary);';
          sec.bullets.forEach((bullet) => {
            const li = document.createElement('li');
            li.style.marginBottom = '4px';
            li.style.lineHeight = '1.6';
            li.textContent = bullet;
            bulletList.appendChild(li);
          });
          block.appendChild(bulletList);
        }

        // Render numbered_points if present
        if (sec.numbered_points && sec.numbered_points.length > 0) {
          const olList = document.createElement('ol');
          olList.className = 'section-numbered-list';
          olList.style.cssText = 'margin: 8px 0; padding-left: 24px; color: var(--text-secondary);';
          sec.numbered_points.forEach((point) => {
            const li = document.createElement('li');
            li.style.marginBottom = '4px';
            li.style.lineHeight = '1.6';
            li.textContent = point;
            olList.appendChild(li);
          });
          block.appendChild(olList);
        }

        // Render subsections if present
        if (sec.subsections && sec.subsections.length > 0) {
          sec.subsections.forEach((sub) => {
            const subDiv = document.createElement('div');
            subDiv.className = 'subsection-block';
            subDiv.style.cssText = 'margin: 12px 0 12px 16px; padding: 8px 12px; border-left: 2px solid var(--accent-soft); border-radius: 0 var(--r-sm) var(--r-sm) 0;';
            const subHeading = document.createElement('div');
            subHeading.className = 'subsection-heading';
            subHeading.style.cssText = 'font-weight: 600; font-size: var(--fs-md); color: var(--text-primary); margin-bottom: 6px;';
            subHeading.textContent = sub.heading || '';
            subDiv.appendChild(subHeading);
            if (sub.content) {
              const subContent = document.createElement('div');
              subContent.className = 'subsection-content';
              subContent.style.cssText = 'font-size: var(--fs-base); color: var(--text-secondary); line-height: 1.6;';
              subContent.textContent = sub.content;
              subDiv.appendChild(subContent);
            }
            block.appendChild(subDiv);
          });
        }

        // Actions
'@
if ($content -ne $original -or $changes -gt 0) { $original2 = $content; if ($content -ne (get-variable -name 'original2' -valueOnly -scope 1 2>$null)) { Write-Host "  [FIX 2] Added bullets/numbered_points/subsections rendering" -ForegroundColor Green; $changes++ } }

# Actually let me track changes more simply
$content = 'dummy' # Reset tracking
$content = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
$changes = 0

# === FIX 1: Empty paragraphs bug ===
if ($content -match '(?<pre>        const paragraphs = )sec\.paragraphs \|\| \[sec\.content \|\| ""\]') {
    $content = $content -replace '(?<=        const paragraphs = )sec\.paragraphs \|\| \[sec\.content \|\| ""\]', '(sec.paragraphs && sec.paragraphs.length > 0) ? sec.paragraphs : [sec.content || ""]'
    Write-Host "  [FIX 1] Fixed empty paragraphs bug" -ForegroundColor Green
    $changes++
}

# === FIX 2: bullets/numbered_points/subsections rendering ===
if ($content -match '\s{8}\)\);\r?\n\s{8}\r?\n\s{8}// Actions') {
    $content = $content -replace '(?s)(\s{8}\)\);\r?\n\s{8}\r?\n\s{8}// Actions)', "`r`n        })();`r`n`r`n        // Render bullets if present`r`n        if (sec.bullets && sec.bullets.length > 0) {`r`n          const bulletList = document.createElement('ul');`r`n          bulletList.className = 'section-bullet-list';`r`n          bulletList.style.cssText = 'margin: 8px 0; padding-left: 24px; color: var(--text-secondary);';`r`n          sec.bullets.forEach((bullet) => {`r`n            const li = document.createElement('li');`r`n            li.style.marginBottom = '4px';`r`n            li.style.lineHeight = '1.6';`r`n            li.textContent = bullet;`r`n            bulletList.appendChild(li);`r`n          });`r`n          block.appendChild(bulletList);`r`n        }`r`n`r`n        // Render numbered_points if present`r`n        if (sec.numbered_points && sec.numbered_points.length > 0) {`r`n          const olList = document.createElement('ol');`r`n          olList.className = 'section-numbered-list';`r`n          olList.style.cssText = 'margin: 8px 0; padding-left: 24px; color: var(--text-secondary);';`r`n          sec.numbered_points.forEach((point) => {`r`n            const li = document.createElement('li');`r`n            li.style.marginBottom = '4px';`r`n            li.style.lineHeight = '1.6';`r`n            li.textContent = point;`r`n            olList.appendChild(li);`r`n          });`r`n          block.appendChild(olList);`r`n        }`r`n`r`n        // Render subsections if present`r`n        if (sec.subsections && sec.subsections.length > 0) {`r`n          sec.subsections.forEach((sub) => {`r`n            const subDiv = document.createElement('div');`r`n            subDiv.className = 'subsection-block';`r`n            subDiv.style.cssText = 'margin: 12px 0 12px 16px; padding: 8px 12px; border-left: 2px solid var(--accent-soft); border-radius: 0 var(--r-sm) var(--r-sm) 0;';`r`n            const subHeading = document.createElement('div');`r`n            subHeading.className = 'subsection-heading';`r`n            subHeading.style.cssText = 'font-weight: 600; font-size: var(--fs-md); color: var(--text-primary); margin-bottom: 6px;';`r`n            subHeading.textContent = sub.heading || '';`r`n            subDiv.appendChild(subHeading);`r`n            if (sub.content) {`r`n              const subContent = document.createElement('div');`r`n              subContent.className = 'subsection-content';`r`n              subContent.style.cssText = 'font-size: var(--fs-base); color: var(--text-secondary); line-height: 1.6;';`r`n              subContent.textContent = sub.content;`r`n              subDiv.appendChild(subContent);`r`n            }`r`n            block.appendChild(subDiv);`r`n          });`r`n        }`r`n`r`n        // Actions"
    Write-Host "  [FIX 2] Added bullets/numbered_points/subsections rendering" -ForegroundColor Green
    $changes++
}

# === FIX 3: saveEditorCanvasToState - preserve Kotlin fields ===
$old3 = '        const existingSec = ch.sections[bIdx] || {};'
if ($content -match [regex]::Escape($old3)) {
    $pattern3 = '(?s)(        const existingSec = ch\.sections\[bIdx\] \|\| \{\};.*?        return \{)'
    $replacement = "        const existingSec = ch.sections[bIdx] || {};`r`n        return {"
    $content = $content -replace $pattern3, $replacement
    # Now fix the return object to include all fields
    $content = $content -replace '(?s)(        return \{\r?\n          heading: heading,\r?\n          content: )paragraphs\[0\] \|\| ""', "`$1paragraphs.length > 0 ? paragraphs[0] : (existingSec.content || '""')"
    $content = $content -replace '(?s)(          paragraphs: )paragraphs', "`$1paragraphs.length > 0 ? paragraphs : (existingSec.paragraphs || [])"
    $content = $content -replace '(?s)(          table: existingSec\.table \|\| null,\r?\n          figures: existingSec\.figures \|\| \[\])', "`$1,`r`n          bullets: existingSec.bullets || [],`r`n          numbered_points: existingSec.numbered_points || [],`r`n          subsections: existingSec.subsections || [],`r`n          references: existingSec.references || []"
    Write-Host "  [FIX 3] Updated saveEditorCanvasToState to preserve Kotlin fields" -ForegroundColor Green
    $changes++
}

# === FIX 4: Handle both variable formats ===
$old4 = "`$name = trim((string)(`$item['variable_name'] ?? ''));"
if ($content -match [regex]::Escape($old4)) {
    $content = $content -replace [regex]::Escape("`$name = trim((string)(`$item['variable_name'] ?? ''));"), "`$name = trim((string)(`$item['variable_name'] ?? `$item['name'] ?? ''));"
    $content = $content -replace [regex]::Escape("`$val = trim((string)(`$item['variable_value'] ?? ''));"), "`$val = trim((string)(`$item['variable_value'] ?? `$item['value'] ?? ''));"
    Write-Host "  [FIX 4] Added support for Kotlin Variable format (name/value)" -ForegroundColor Green
    $changes++
}

# === FIX 5: Add CSS ===
if ($content -match '\.section-paragraph-block \{') {
    $content = $content -replace '(?s)(\.section-paragraph-block \{[^}]+\}\n    \})', "`$1`r`n    .section-bullet-list { list-style: disc; margin: 8px 0; padding-left: 24px; color: var(--text-secondary); }`r`n    .section-numbered-list { list-style: decimal; margin: 8px 0; padding-left: 24px; color: var(--text-secondary); }`r`n    .subsection-block { margin: 12px 0 12px 16px; padding: 8px 12px; border-left: 2px solid rgba(99,102,241,0.25); border-radius: 0 var(--r-sm) var(--r-sm) 0; }`r`n    .subsection-heading { font-weight: 600; font-size: var(--fs-md); color: var(--text-primary); margin-bottom: 6px; }`r`n    .subsection-content { font-size: var(--fs-base); color: var(--text-secondary); line-height: 1.6; }"
    Write-Host "  [FIX 5] Added CSS for new section elements" -ForegroundColor Green
    $changes++
}

# Write the file back
if ($changes -gt 0) {
    [System.IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::UTF8)
    Write-Host "`n=== SUCCESS: $changes fixes applied ===" -ForegroundColor Cyan
} else {
    Write-Host "`n=== NO CHANGES MADE (patterns didn't match) ===" -ForegroundColor Red
}
