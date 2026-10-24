[CmdletBinding()]
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$ReportPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'validation-report.json')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:Checks = [System.Collections.Generic.List[object]]::new()
$script:Failures = [System.Collections.Generic.List[string]]::new()

function Add-Check {
    param([string]$Id, [bool]$Passed, [string]$Detail)
    $script:Checks.Add([ordered]@{ id = $Id; passed = $Passed; detail = $Detail })
    if (-not $Passed) { $script:Failures.Add("$Id`: $Detail") }
}

function Read-JsonObject {
    param([string]$Path)
    return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json -Depth 100
}

function Test-Instance {
    param([string]$InstancePath, [string]$SchemaPath)
    try {
        return [bool](Test-Json -LiteralPath $InstancePath -SchemaFile $SchemaPath -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

function Test-JsonTextInstance {
    param([string]$InstancePath, [string]$SchemaPath)
    try {
        $json = Get-Content -Raw -LiteralPath $InstancePath
        return [bool](Test-Json -Json $json -SchemaFile $SchemaPath -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

$script:TierRank = @{ routine = 0; notable = 1; significant = 2 }

function Get-OptionalProperty {
    param($Object, [string]$Name, $Default)
    if ($Object.PSObject.Properties.Name -contains $Name) { return $Object.$Name }
    return $Default
}

function Test-IsNumber {
    param($Value)
    return ($Value -is [int] -or $Value -is [long] -or $Value -is [double] -or $Value -is [decimal] -or $Value -is [System.Numerics.BigInteger])
}

function Test-SameValue {
    param($Left, $Right)
    if ((Test-IsNumber $Left) -and (Test-IsNumber $Right)) { return ([double]$Left -eq [double]$Right) }
    if ($null -eq $Left -or $null -eq $Right) { return $false }
    if ($Left.GetType() -ne $Right.GetType()) { return $false }
    if ($Left -is [string]) { return $Left -ceq $Right }
    return $Left -eq $Right
}

function Test-UniqueOrdinal {
    param([string[]]$Values)
    $set = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($item in $Values) { if (-not $set.Add($item)) { return $false } }
    return $true
}

function Test-ReviewSemantic {
    param($Value)
    if ($Value.reviewer.independent) {
        if ($Value.reviewer.identity -eq $Value.implementer.identity) { return $false }
        if ($Value.reviewer.context_id -eq $Value.implementer.context_id) { return $false }
        if ($Value.reviewer.independence_basis -match '(?i)renamed.*self|same agent|same context') { return $false }
    }
    if ($Value.decision -eq 'approve' -and $Value.reviewer.independent -and $Value.signature.state -ne 'verified') { return $false }
    $criteria = @(Get-OptionalProperty $Value 'acceptance_criteria' @())
    if (-not (Test-UniqueOrdinal @($criteria | ForEach-Object { $_.id }))) { return $false }
    foreach ($criterion in $criteria) {
        if ($criterion.verdict -eq 'met' -and @($criterion.evidence).Count -eq 0) { return $false }
        if ($Value.decision -eq 'approve' -and $criterion.verdict -eq 'not_met') { return $false }
    }
    return $true
}

function Test-VerificationSemantic {
    param($Value)
    if ($Value.status -eq 'pass') {
        foreach ($check in $Value.checks) {
            if ($check.blocking -and $check.status -ne 'pass') { return $false }
        }
        foreach ($unrun in $Value.unrun_checks) {
            if ($unrun.required) { return $false }
        }
    }
    foreach ($check in $Value.checks) {
        if (($check.PSObject.Properties.Name -contains 'vulnerability_data') -and $check.tool.version -eq 'unknown') { return $false }
    }
    foreach ($sentinel in @(Get-OptionalProperty $Value 'sentinels' @())) {
        if ($sentinel.outcome -eq 'not_measured') {
            if ($Value.status -eq 'pass') { return $false }
            continue
        }
        if ($null -eq $sentinel.observed) { return $false }
        if ($sentinel.comparison -eq 'at_most') {
            if (-not ((Test-IsNumber $sentinel.expected) -and (Test-IsNumber $sentinel.observed))) { return $false }
            $within = ([double]$sentinel.observed -le [double]$sentinel.expected)
        } else {
            $within = Test-SameValue $sentinel.observed $sentinel.expected
        }
        if (($sentinel.outcome -eq 'pass') -ne $within) { return $false }
        if ($Value.status -eq 'pass' -and $sentinel.outcome -ne 'pass') { return $false }
    }
    return $true
}

function Test-RunManifestSemantic {
    param($Value)
    if ($script:TierRank[$Value.approved_tier] -lt $script:TierRank[$Value.computed_tier]) { return $false }
    if ($Value.status -eq 'succeeded') {
        if ($null -eq $Value.completed_at) { return $false }
        foreach ($stage in $Value.stages) {
            if ($stage.outcome -notin @('pass', 'not_required')) { return $false }
        }
        $approvals = @($Value.approvals)
        if (@($approvals | Where-Object { $_.decision -eq 'reject' }).Count -gt 0) { return $false }
        if ($Value.approved_tier -eq 'significant' -and @($approvals | Where-Object { $_.decision -eq 'approve' -and $_.tier -eq 'significant' }).Count -eq 0) { return $false }
    }
    return $true
}

function Test-ProcessContractSemantic {
    param($Value)
    $stageIds = @($Value.stages | ForEach-Object { $_.id })
    if (-not (Test-UniqueOrdinal $stageIds)) { return $false }
    $stageById = @{}
    foreach ($stage in $Value.stages) { $stageById[$stage.id] = $stage }
    if ($Value.rework_limit -gt 2) { return $false }
    $significant = $Value.approvals.significant
    if (-not $significant.run_approval_required -or $significant.minimum_approvals -lt 1) { return $false }
    foreach ($rule in $Value.approvals.PSObject.Properties) {
        if ($rule.Value.run_approval_required) {
            if ($rule.Value.minimum_approvals -lt 1) { return $false }
            if ($null -eq $rule.Value.before_stage -or $stageIds -cnotcontains $rule.Value.before_stage) { return $false }
            if (@($stageById[$rule.Value.before_stage].applies_to_tiers) -notcontains $rule.Name) { return $false }
        }
    }
    foreach ($stage in $Value.stages) {
        if (@($stage.produces) -contains 'review_record' -and -not $stage.fresh_context) { return $false }
    }
    return $true
}

function Test-ProfileSemantic {
    param($Value)
    $involvement = Get-OptionalProperty $Value 'human_involvement' $null
    if ($null -eq $involvement) { return $true }
    $timers = $involvement.timers
    if (-not ($timers.reminder_hours -lt $timers.escalation_hours -and $timers.escalation_hours -lt $timers.expiry_hours)) { return $false }
    $rules = $involvement.tier_rules
    if ($rules.routine_max_changed_lines -gt $rules.notable_max_changed_lines) { return $false }
    $protected = [System.Collections.Generic.HashSet[string]]::new([string[]]@($rules.protected_paths), [StringComparer]::Ordinal)
    foreach ($path in $rules.routine_path_allowlist) { if ($protected.Contains($path)) { return $false } }
    if (@($involvement.roles.significant.stakeholders).Count -eq 0) { return $false }
    if (@($involvement.roles.notable.reviewers).Count -eq 0) { return $false }
    return $true
}

function Test-WaiverSemantic {
    param($Value, [hashtable]$ControlById)
    if ($Value.owner.identity -eq $Value.approver.identity) { return $false }
    $issued = [DateTimeOffset]$Value.issued_at
    $expires = [DateTimeOffset]$Value.expires_at
    if ($expires -le $issued) { return $false }
    if ($Value.status -eq 'active' -and $Value.signature.state -ne 'verified') { return $false }
    foreach ($id in $Value.control_ids) {
        if (-not $ControlById.ContainsKey($id)) { return $false }
        if (-not [bool]$ControlById[$id].exception_eligible) { return $false }
    }
    return $true
}

function Test-EffectSemantic {
    param($Value)
    if ($Value.status -eq 'complete') {
        if ($Value.cleanup.status -in @('failed', 'partial', 'planned')) { return $false }
        foreach ($effect in $Value.external_effects) {
            if ($effect.requested -and -not $effect.authorized) { return $false }
            if ($effect.requested -and $effect.status -notin @('confirmed', 'reverted', 'not_executed')) { return $false }
        }
    }
    if ($Value.delegation.may_expand_authority) { return $false }
    return $true
}

function Test-VerifierConfigSemantic {
    param($Value)
    foreach ($tier in $Value.tiers.PSObject.Properties) {
        if (-not (Test-UniqueOrdinal @($tier.Value.checks | ForEach-Object { $_.id }))) { return $false }
    }
    return $true
}

function Test-MigrationRecordSemantic {
    param($Value)
    if (($Value.kind -eq 'rollback') -ne ($null -ne $Value.rolls_back)) { return $false }
    $applied = $Value.status -eq 'applied'
    if ($applied -and $Value.kind -eq 'update' -and $null -eq $Value.snapshot_dir) { return $false }
    foreach ($action in $Value.actions) {
        $kind = $action.action
        if ($applied -and $kind -eq 'CONFLICT') { return $false }
        if ($action.ownership -eq 'project-owned' -and $kind -notin @('KEEP', 'SKIP', 'SUGGEST', 'ADD', 'REMOVE')) { return $false }
        if ($kind -eq 'REMOVE' -and $Value.kind -ne 'rollback') { return $false }
        if ($kind -eq 'ADD' -and $null -ne $action.before_digest) { return $false }
        if ($applied -and $kind -in @('ADD', 'REPLACE', 'MERGE', 'RESTORE') -and $null -eq $action.after_digest) { return $false }
        if ($kind -in @('REPLACE', 'MERGE', 'RESTORE', 'REMOVE') -and $null -eq $action.before_digest) { return $false }
    }
    return $true
}

function Test-GateResultSemantic {
    param($Value)
    $effective = [Math]::Max($script:TierRank[$Value.computed_tier], $script:TierRank[$Value.approved_tier])
    if ($script:TierRank[$Value.effective_tier] -ne $effective) { return $false }
    $new = @($Value.findings | Where-Object { $_.status -eq 'new' })
    if ($Value.status -eq 'pass' -and $new.Count -gt 0) { return $false }
    if ($Value.status -in @('fail', 'report_only') -and $new.Count -eq 0) { return $false }
    if (@($Value.findings | Where-Object { $_.status -eq 'known' -and -not $_.ratchetable }).Count -gt 0) { return $false }
    if ($Value.status -eq 'report_only' -and $Value.mode -notin @('report', 'ratchet')) { return $false }
    return $true
}

function Test-GateBaselineSemantic {
    param($Value)
    return (Test-UniqueOrdinal @($Value.findings | ForEach-Object { $_.fingerprint }))
}

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$schemaDir = Join-Path $rootPath 'schemas'
$exampleDir = Join-Path $rootPath 'examples'

$schemas = @{
    profile = Join-Path $schemaDir 'project-assurance-profile.schema.json'
    catalog = Join-Path $schemaDir 'control-catalog.schema.json'
    matrix = Join-Path $schemaDir 'change-class-evidence-matrix.schema.json'
    review = Join-Path $schemaDir 'review-record.schema.json'
    verification = Join-Path $schemaDir 'verification-result.schema.json'
    waiver = Join-Path $schemaDir 'waiver.schema.json'
    effect = Join-Path $schemaDir 'agent-effect-manifest.schema.json'
    manifest = Join-Path $schemaDir 'assurance-system-manifest.schema.json'
    'run-manifest' = Join-Path $schemaDir 'run-manifest.schema.json'
    'process-contract' = Join-Path $schemaDir 'process-contract.schema.json'
    'verifier-config' = Join-Path $schemaDir 'verifier-config.schema.json'
    'migration-record' = Join-Path $schemaDir 'migration-record.schema.json'
    'gate-result' = Join-Path $schemaDir 'gate-result.schema.json'
    'gate-baseline' = Join-Path $schemaDir 'gate-baseline.schema.json'
}

foreach ($entry in $schemas.GetEnumerator()) {
    $syntax = $false
    try { $syntax = [bool](Test-Json -LiteralPath $entry.Value -ErrorAction SilentlyContinue) } catch { $syntax = $false }
    Add-Check "schema-syntax-$($entry.Key)" $syntax $entry.Value
}

$profileTemplate = Join-Path $rootPath 'project-assurance-profile.template.json'
Add-Check 'profile-template-schema' (Test-Instance $profileTemplate $schemas.profile) 'Template conforms to project profile schema.'

$processTemplate = Join-Path $rootPath 'process-contract.template.json'
$processTemplateValid = Test-Instance $processTemplate $schemas['process-contract']
if ($processTemplateValid) { $processTemplateValid = [bool](Test-ProcessContractSemantic (Read-JsonObject $processTemplate)) }
Add-Check 'process-contract-template-valid' $processTemplateValid 'Default process contract conforms to its schema and semantic rules.'

$manifestTemplate = Join-Path $rootPath 'assurance-system-manifest.template.json'
Add-Check 'manifest-template-schema' (Test-Instance $manifestTemplate $schemas.manifest) 'Installed-system manifest template conforms to its schema.'

$catalogPath = Join-Path $rootPath 'control-catalog.template.yaml'
Add-Check 'catalog-json-compatible-yaml-schema' (Test-JsonTextInstance $catalogPath $schemas.catalog) 'Catalog is JSON-compatible YAML 1.2 and conforms to schema.'

$matrixPath = Join-Path $rootPath 'change-class-evidence-matrix.json'
Add-Check 'change-matrix-schema' (Test-Instance $matrixPath $schemas.matrix) 'Change-class matrix conforms to schema.'

$catalog = Read-JsonObject $catalogPath
$controlIds = @($catalog.controls | ForEach-Object { $_.id })
$uniqueControlIds = @($controlIds | Sort-Object -Unique)
Add-Check 'control-ids-unique' ($controlIds.Count -eq $uniqueControlIds.Count) "$($controlIds.Count) controls; $($uniqueControlIds.Count) unique IDs."

$vaguePattern = '(?i)\bwhen feasible\b|\bas applicable\b|\bwhen practical\b|\bproportional to risk\b'
$vagueControls = @($catalog.controls | Where-Object { $_.action -match $vaguePattern } | ForEach-Object { $_.id })
Add-Check 'control-actions-no-vague-escape-hatches' ($vagueControls.Count -eq 0) $(if ($vagueControls.Count -eq 0) { 'No prohibited vague phrase in control actions.' } else { "Found in: $($vagueControls -join ', ')" })

$badBlockingStrength = @($catalog.controls | Where-Object { $_.blocking -and $_.strength -notin @('MUST', 'MUST NOT') } | ForEach-Object { $_.id })
Add-Check 'blocking-controls-normative' ($badBlockingStrength.Count -eq 0) $(if ($badBlockingStrength.Count -eq 0) { 'All blocking controls use MUST or MUST NOT.' } else { "Invalid: $($badBlockingStrength -join ', ')" })

$controlById = @{}
foreach ($control in $catalog.controls) { $controlById[$control.id] = $control }

$requiredCoverageControls = @(
    'GOV-001', 'GOV-002', 'GOV-004', 'GOV-005', 'GOV-006', 'GOV-007', 'GOV-008', 'GOV-009', 'GOV-010',
    'DES-001', 'DES-002', 'DES-003',
    'ENG-003', 'ENG-004', 'ENG-006', 'ENG-007', 'ENG-008', 'ENG-009', 'ENG-010', 'ENG-011',
    'VER-001', 'VER-003', 'VER-004', 'SEC-002', 'SEC-003', 'SEC-004', 'SEC-006', 'SEC-007',
    'DAT-001', 'DAT-002', 'DAT-003', 'DAT-004',
    'AGT-001', 'AGT-002', 'AGT-003', 'AGT-004', 'AGT-005', 'AGT-006', 'AGT-007',
    'AGT-008', 'AGT-009', 'AGT-010', 'AGT-011', 'AGT-012',
    'OPS-001', 'OPS-002', 'OPS-003', 'OPS-004', 'OPS-005', 'OPS-006',
    'REL-001', 'REL-002', 'REL-003'
)
$missingCoverageControls = @($requiredCoverageControls | Where-Object { -not $controlById.ContainsKey($_) })
Add-Check 'required-policy-coverage-controls-present' ($missingCoverageControls.Count -eq 0) $(if ($missingCoverageControls.Count -eq 0) { 'All required engineering and corporate-agent policy areas have stable controls.' } else { $missingCoverageControls -join ', ' })

$profileExamples = @(
    (Join-Path $exampleDir 'project-profile-web-service.valid.json')
    (Join-Path $exampleDir 'project-profile-corporate-agent.valid.json')
)
foreach ($path in $profileExamples) {
    Add-Check "profile-example-$([IO.Path]::GetFileNameWithoutExtension($path))" (Test-Instance $path $schemas.profile) $path
    $description = (Read-JsonObject $path).project.description
    Add-Check "profile-example-nonnormative-$([IO.Path]::GetFileNameWithoutExtension($path))" ($description -match '(?i)non-normative') 'Example description declares non-normative status.'
}

$badProfileSemantics = @(@($profileTemplate) + $profileExamples | Where-Object { -not (Test-ProfileSemantic (Read-JsonObject $_)) } | ForEach-Object { [IO.Path]::GetFileName($_) })
Add-Check 'profile-delivery-blocks-semantic' ($badProfileSemantics.Count -eq 0) $(if ($badProfileSemantics.Count -eq 0) { 'Template and example human_involvement blocks satisfy timer, threshold, path, and role rules.' } else { $badProfileSemantics -join ', ' })

$manifestValid = Join-Path $exampleDir 'assurance-system-manifest.valid.json'
$manifestInvalid = Join-Path $exampleDir 'assurance-system-manifest.invalid.json'
Add-Check 'manifest-valid-accepted' (Test-Instance $manifestValid $schemas.manifest) 'Positive installed-system manifest fixture passes schema validation.'
Add-Check 'manifest-invalid-rejected' (-not (Test-Instance $manifestInvalid $schemas.manifest)) 'Negative installed-system manifest fixture is rejected.'

$matrix = Read-JsonObject $matrixPath
$classes = @($matrix.classes | ForEach-Object { $_.class })
Add-Check 'change-classes-unique-and-complete' (($classes | Sort-Object -Unique).Count -eq 12) 'All twelve required change classes occur exactly once.'
$triggerIds = @($matrix.classes.escalation_triggers | ForEach-Object { $_.id })
Add-Check 'matrix-trigger-ids-unique' ($triggerIds.Count -eq ($triggerIds | Sort-Object -Unique).Count) "$($triggerIds.Count) escalation triggers are unique."

$fixtureSets = @(
    @{ Name='review-record'; Schema=$schemas.review; Semantic={ param($v) Test-ReviewSemantic $v } },
    @{ Name='verification-result'; Schema=$schemas.verification; Semantic={ param($v) Test-VerificationSemantic $v } },
    @{ Name='waiver'; Schema=$schemas.waiver; Semantic={ param($v) Test-WaiverSemantic $v $controlById } },
    @{ Name='agent-effect-manifest'; Schema=$schemas.effect; Semantic={ param($v) Test-EffectSemantic $v } },
    @{ Name='run-manifest'; Schema=$schemas['run-manifest']; Semantic={ param($v) Test-RunManifestSemantic $v } },
    @{ Name='process-contract'; Schema=$schemas['process-contract']; Semantic={ param($v) Test-ProcessContractSemantic $v } },
    @{ Name='project-profile'; Schema=$schemas.profile; Semantic={ param($v) Test-ProfileSemantic $v } },
    @{ Name='verifier-config'; Schema=$schemas['verifier-config']; Semantic={ param($v) Test-VerifierConfigSemantic $v } },
    @{ Name='migration-record'; Schema=$schemas['migration-record']; Semantic={ param($v) Test-MigrationRecordSemantic $v } },
    @{ Name='assurance-system-manifest'; Schema=$schemas.manifest; Semantic={ param($v) $true } },
    @{ Name='gate-result'; Schema=$schemas['gate-result']; Semantic={ param($v) Test-GateResultSemantic $v } },
    @{ Name='gate-baseline'; Schema=$schemas['gate-baseline']; Semantic={ param($v) Test-GateBaselineSemantic $v } }
)
$explicitlyChecked = @('assurance-system-manifest.valid.json', 'assurance-system-manifest.invalid.json')

# <name>.valid.json / <name>.invalid.json keep their original check IDs; <name>.valid-<case>.json adds <name>-valid-<case>-accepted.
foreach ($set in $fixtureSets) {
    foreach ($kind in @('valid', 'invalid')) {
        $prefix = "$($set.Name).$kind"
        $names = [string[]]@(Get-ChildItem -LiteralPath $exampleDir -File | Where-Object { $_.Name.StartsWith($prefix, [StringComparison]::Ordinal) -and $_.Name.EndsWith('.json', [StringComparison]::Ordinal) -and $explicitlyChecked -notcontains $_.Name } | ForEach-Object { $_.Name })
        [Array]::Sort($names, [StringComparer]::Ordinal)
        if ($kind -eq 'invalid') { Add-Check "$($set.Name)-negative-fixtures-present" ($names.Count -gt 0) "$($names.Count) negative fixture(s)." }
        foreach ($name in $names) {
            $path = Join-Path $exampleDir $name
            $case = $name.Substring($prefix.Length, $name.Length - $prefix.Length - '.json'.Length)
            $schemaOk = Test-Instance $path $set.Schema
            $semanticOk = $false
            if ($schemaOk) { $semanticOk = [bool](& $set.Semantic (Read-JsonObject $path)) }
            if ($kind -eq 'valid') {
                Add-Check "$($set.Name)-valid$case-accepted" ($schemaOk -and $semanticOk) "$name`: positive fixture passes schema and semantic validation."
            } else {
                Add-Check "$($set.Name)-invalid$case-rejected" (-not ($schemaOk -and $semanticOk)) "$name`: schema=$schemaOk semantic=$semanticOk; combined validation rejects it."
            }
        }
    }
}

$knownControls = [System.Collections.Generic.HashSet[string]]::new([string[]]$controlIds)
$unknownReferences = [System.Collections.Generic.List[string]]::new()
$controlFamilies = @($controlIds | ForEach-Object { ($_ -split '-')[0] } | Sort-Object -Unique)
$controlReferencePattern = '\b(?:' + (($controlFamilies | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')-[0-9]{3}\b'
Get-ChildItem -LiteralPath $rootPath -File -Recurse | Where-Object { $_.Extension -in @('.md', '.json', '.yaml') } | ForEach-Object {
    $text = Get-Content -Raw -LiteralPath $_.FullName
    foreach ($match in [regex]::Matches($text, $controlReferencePattern)) {
        if (-not $knownControls.Contains($match.Value)) { $unknownReferences.Add("$([IO.Path]::GetRelativePath($rootPath, $_.FullName)):$($match.Value)") }
    }
}
$profile = Read-JsonObject $profileTemplate
foreach ($id in $profile.exceptions.prohibited_control_ids) {
    if (-not $knownControls.Contains($id)) { $unknownReferences.Add("profile-template:$id") }
}
Add-Check 'example-control-references-known' ($unknownReferences.Count -eq 0) $(if ($unknownReferences.Count -eq 0) { 'All referenced control IDs exist.' } else { $unknownReferences -join ', ' })

$ineligibleMarkedProhibited = @($profile.exceptions.prohibited_control_ids | Where-Object { $controlById.ContainsKey($_) -and [bool]$controlById[$_].exception_eligible })
Add-Check 'template-prohibited-controls-not-eligible' ($ineligibleMarkedProhibited.Count -eq 0) $(if ($ineligibleMarkedProhibited.Count -eq 0) { 'Profile-prohibited controls are catalog-ineligible.' } else { "Mismatch: $($ineligibleMarkedProhibited -join ', ')" })

$profileExceptionErrors = [System.Collections.Generic.List[string]]::new()
foreach ($path in @($profileTemplate) + $profileExamples) {
    $candidate = Read-JsonObject $path
    foreach ($id in $candidate.exceptions.prohibited_control_ids) {
        if (-not $controlById.ContainsKey($id)) { $profileExceptionErrors.Add("$([IO.Path]::GetFileName($path)):$id missing") }
        elseif ([bool]$controlById[$id].exception_eligible) { $profileExceptionErrors.Add("$([IO.Path]::GetFileName($path)):$id catalog-eligible") }
    }
}
Add-Check 'profile-prohibited-controls-consistent' ($profileExceptionErrors.Count -eq 0) $(if ($profileExceptionErrors.Count -eq 0) { 'All template/example prohibited controls exist and are catalog-ineligible.' } else { $profileExceptionErrors -join ', ' })

$agentsPath = Join-Path $rootPath 'AGENTS.template.md'
$agentsRaw = [IO.File]::ReadAllBytes($agentsPath)
$agentsBytes = $agentsRaw.Length
for ($i = 0; $i -lt $agentsRaw.Length - 1; $i++) { if ($agentsRaw[$i] -eq 13 -and $agentsRaw[$i + 1] -eq 10) { $agentsBytes-- } }
Add-Check 'agents-template-size-4-to-8-kib' ($agentsBytes -ge 4096 -and $agentsBytes -le 8192) "$agentsBytes bytes with LF line endings (required range 4096..8192; detailed policy remains outside the runner entry instructions)."

$missingLinks = [System.Collections.Generic.List[string]]::new()
Get-ChildItem -LiteralPath $rootPath -Filter '*.md' -Recurse | ForEach-Object {
    $source = $_
    if ($source.Name -in @('project-start-here.template.md', 'project-readme.template.md')) { return }
    $text = Get-Content -Raw -LiteralPath $source.FullName
    foreach ($match in [regex]::Matches($text, '\[[^\]]+\]\(([^)]+)\)')) {
        $target = $match.Groups[1].Value
        if ($target -match '^(https?://|mailto:|#)') { continue }
        $withoutAnchor = ($target -split '#')[0]
        if ([string]::IsNullOrWhiteSpace($withoutAnchor)) { continue }
        $decoded = [Uri]::UnescapeDataString($withoutAnchor)
        $resolved = Join-Path $source.DirectoryName $decoded
        if (-not (Test-Path -LiteralPath $resolved)) { $missingLinks.Add("$($source.Name) -> $target") }
    }
}
Add-Check 'relative-markdown-links-resolve' ($missingLinks.Count -eq 0) $(if ($missingLinks.Count -eq 0) { 'All relative Markdown links resolve.' } else { $missingLinks -join '; ' })

$architectureTemplate = Join-Path $rootPath 'architecture-assurance.template.md'
$architectureText = if (Test-Path -LiteralPath $architectureTemplate) { Get-Content -Raw -LiteralPath $architectureTemplate } else { '' }
$requiredArchitectureMarkers = @('## Required views', '### System context', '### Container/component and dependency view', '### Deployment and environment view', '### Data-flow and trust-boundary view', '## Critical behavioral flows', '## Threat and abuse register', '## Diagram-to-reality and contract traceability', '```mermaid')
$missingArchitectureMarkers = @($requiredArchitectureMarkers | Where-Object { -not $architectureText.Contains($_) })
Add-Check 'architecture-template-required-sections' ($missingArchitectureMarkers.Count -eq 0) $(if ($missingArchitectureMarkers.Count -eq 0) { 'Architecture template contains structural views, conditional behavioral flows, threat register, traceability, and diagram-as-code examples.' } else { $missingArchitectureMarkers -join ', ' })

$onboardingMarkers = [ordered]@{
    'START-HERE.md' = @('## Five required inputs', '## Facts the agent may derive', '## Result')
    'bootstrap-prompt.md' = @('Lead a short discovery/bootstrap interview', 'Stop before coding and report')
    'profile-selection-guide.md' = @('## Selection algorithm', '## Lightweight', '## General', '## Corporate/high-risk', '## Burden rule')
    'installation-and-update-guide.md' = @('## Canonical greenfield structure', '## Existing repository adoption', '## Ownership and safe update', '## Optional safe scaffolder')
}
$missingOnboarding = [System.Collections.Generic.List[string]]::new()
foreach ($entry in $onboardingMarkers.GetEnumerator()) {
    $path = Join-Path $rootPath $entry.Key
    $text = if (Test-Path -LiteralPath $path) { Get-Content -Raw -LiteralPath $path } else { '' }
    foreach ($marker in $entry.Value) {
        if (-not $text.Contains($marker)) { $missingOnboarding.Add("$($entry.Key):$marker") }
    }
}
Add-Check 'onboarding-workflow-required-sections' ($missingOnboarding.Count -eq 0) $(if ($missingOnboarding.Count -eq 0) { 'Onboarding defines inputs, inference boundaries, preset selection, greenfield/existing installation, and safe updates.' } else { $missingOnboarding -join ', ' })

$lifecycleMarkers = [ordered]@{
    'project-discovery.template.md' = @('## Minimum discovery', '## Assurance selection worksheet', '## Open decisions and stop conditions')
    'product-brief.template.md' = @('## Problem and users', '## Product outcome', '## Scope')
    'requirements.template.md' = @('## Functional requirements', '## Quality requirements and budgets', '## Traceability')
    'roadmap.template.md' = @('## Phase plan', '## Decision gates')
    'test-strategy.template.md' = @('## Verification tiers', '## Requirement and risk coverage', '## Unrun checks and limitations')
    'adr.template.md' = @('## Context', '## Options considered', '## Decision', '## Consequences and controls')
    'project-status.template.md' = @('## Current outcome', '## Verification state', '## Next approved action')
}
$missingLifecycle = [System.Collections.Generic.List[string]]::new()
foreach ($entry in $lifecycleMarkers.GetEnumerator()) {
    $path = Join-Path $rootPath $entry.Key
    $text = if (Test-Path -LiteralPath $path) { Get-Content -Raw -LiteralPath $path } else { '' }
    foreach ($marker in $entry.Value) {
        if (-not $text.Contains($marker)) { $missingLifecycle.Add("$($entry.Key):$marker") }
    }
}
Add-Check 'precode-lifecycle-templates-required-sections' ($missingLifecycle.Count -eq 0) $(if ($missingLifecycle.Count -eq 0) { 'Discovery, product, requirements, roadmap, test, ADR, and status templates contain required decision/evidence sections.' } else { $missingLifecycle -join ', ' })

$workItemPath = Join-Path $rootPath 'work-item.template.md'
$workItemText = if (Test-Path -LiteralPath $workItemPath) { Get-Content -Raw -LiteralPath $workItemPath } else { '' }
$workItemMarkers = @('## Acceptance criteria', '`AC-1`', '`met`, `not_met`, or `not_verifiable`', '## Value check', '## Kill or rethink criteria', '## Rigor budget', '`light | standard | full`')
$missingWorkItem = @($workItemMarkers | Where-Object { -not $workItemText.Contains($_) })
Add-Check 'work-item-template-delivery-sections' ($missingWorkItem.Count -eq 0) $(if ($missingWorkItem.Count -eq 0) { 'Work-item template contains acceptance criteria, value check, kill or rethink criteria, and rigor budget.' } else { $missingWorkItem -join ', ' })

$guardrailMarkers = @('two-strike rule', 'rigor budget', 're-entry trigger')
$missingGuardrails = [System.Collections.Generic.List[string]]::new()
foreach ($name in @('AGENTS.template.md', 'generalized-development-assurance-guidelines.md')) {
    $path = Join-Path $rootPath $name
    $text = if (Test-Path -LiteralPath $path) { (Get-Content -Raw -LiteralPath $path).ToLowerInvariant() } else { '' }
    foreach ($marker in $guardrailMarkers) {
        if (-not $text.Contains($marker)) { $missingGuardrails.Add("$name`:$marker") }
    }
}
Add-Check 'process-guardrails-present' ($missingGuardrails.Count -eq 0) $(if ($missingGuardrails.Count -eq 0) { 'AGENTS template and guidelines state the two-strike rule, rigor budget stop, and re-entry triggers.' } else { $missingGuardrails -join ', ' })

$scaffoldPath = Join-Path $rootPath 'tools/scaffold_project.py'
$scaffoldText = if (Test-Path -LiteralPath $scaffoldPath) { Get-Content -Raw -LiteralPath $scaffoldPath } else { '' }
$scaffoldMarkers = @('if args.apply and args.mode == "existing"', 'destination already exists', 'PLAN ONLY', 'is_reparse_or_symlink', 'commonpath')
$missingScaffold = @($scaffoldMarkers | Where-Object { -not $scaffoldText.Contains($_) })
Add-Check 'scaffolder-safety-markers' ($missingScaffold.Count -eq 0) $(if ($missingScaffold.Count -eq 0) { 'Scaffolder is plan-first and contains existing-mode, overwrite, path-containment, and reparse/symlink refusals.' } else { $missingScaffold -join ', ' })

$updateMarkers = @('changed since the plan was reviewed', 'uncommitted change overlaps planned write', 'downgrade refused', 'project file is never overwritten', 'schema migration needed', 'changed after the migration', '--apply is refused without --plan')
$missingUpdate = @($updateMarkers | Where-Object { -not $scaffoldText.Contains($_) })
Add-Check 'scaffolder-update-safety-markers' ($missingUpdate.Count -eq 0) $(if ($missingUpdate.Count -eq 0) { 'Scaffolder refuses stale plans, dirty overlaps, downgrades, schema migrations, unsafe rollbacks, and never writes project-owned files.' } else { $missingUpdate -join ', ' })

$wrapperProblems = [System.Collections.Generic.List[string]]::new()
$wrapperMarkers = [ordered]@{
    'adapters/github/assurance-gate.yml' = @('assurance_gate.py classify', 'assurance_gate.py "${args[@]}"', 'fetch-depth: 0')
    'adapters/gitlab/assurance-gate.gitlab-ci.yml' = @('assurance_gate.py classify', 'assurance_gate.py "$@"', 'GIT_DEPTH: "0"')
}
foreach ($entry in $wrapperMarkers.GetEnumerator()) {
    $path = Join-Path $rootPath $entry.Key
    $text = if (Test-Path -LiteralPath $path) { Get-Content -Raw -LiteralPath $path } else { '' }
    foreach ($marker in $entry.Value) { if (-not $text.Contains($marker)) { $wrapperProblems.Add("$($entry.Key):$marker") } }
    foreach ($line in ($text -split "`n")) {
        $used = [regex]::Match($line, 'uses:\s*([^\s#]+)')
        if ($used.Success -and $used.Groups[1].Value -notmatch '@[0-9a-f]{40}$') { $wrapperProblems.Add("$($entry.Key): action not pinned to a full commit SHA: $($used.Groups[1].Value)") }
    }
}
Add-Check 'ci-gate-wrappers' ($wrapperProblems.Count -eq 0) $(if ($wrapperProblems.Count -eq 0) { 'GitHub and GitLab wrappers call the forge-neutral gate with full history and pin every action to a commit SHA.' } else { $wrapperProblems -join '; ' })

$versionPath = Join-Path $rootPath 'VERSION'
$packageVersion = if (Test-Path -LiteralPath $versionPath) { (Get-Content -Raw -LiteralPath $versionPath).Trim() } else { '' }
$readmeText = Get-Content -Raw -LiteralPath (Join-Path $rootPath 'README.md')
$manifestVersion = (Read-JsonObject $manifestTemplate).system.version
$versionOk = ($packageVersion -match '^[0-9]+\.[0-9]+\.[0-9]+$') -and $readmeText.Contains("Distribution version: ``$packageVersion``") -and ($manifestVersion -eq $packageVersion)
Add-Check 'distribution-version-consistent' $versionOk "VERSION='$packageVersion', manifest template='$manifestVersion', README must state the same distribution version."

$installedValidatorPath = Join-Path $rootPath 'tools/validate_installed_assurance.py'
$installedValidatorText = if (Test-Path -LiteralPath $installedValidatorPath) { Get-Content -Raw -LiteralPath $installedValidatorPath } else { '' }
$installedValidatorMarkers = @('installed-required-artifacts', 'installed-active-placeholders-resolved', 'installed-manifest-lineage', 'installed-control-ids')
$missingInstalledValidator = @($installedValidatorMarkers | Where-Object { -not $installedValidatorText.Contains($_) })
Add-Check 'installed-validator-scope-markers' ($missingInstalledValidator.Count -eq 0) $(if ($missingInstalledValidator.Count -eq 0) { 'Installed validator covers structure, active placeholders, catalog IDs, and provenance lineage.' } else { $missingInstalledValidator -join ', ' })

$requiredFiles = @(
    'README.md', 'START-HERE.md', 'bootstrap-prompt.md', 'profile-selection-guide.md', 'installation-and-update-guide.md',
    'AGENTS.template.md', 'generalized-development-assurance-guidelines.md', 'project-discovery.template.md',
    'product-brief.template.md', 'requirements.template.md', 'roadmap.template.md', 'test-strategy.template.md', 'adr.template.md',
    'project-status.template.md', 'project-start-here.template.md', 'assurance-directory-readme.template.md',
    'project-readme.template.md',
    'project-assurance-profile.template.json', 'assurance-system-manifest.template.json', 'control-catalog.template.yaml', 'work-item.template.md', 'architecture-assurance.template.md',
    'change-class-evidence-matrix.json', 'tiered-verifier-contract.md', 'adoption-guide.md',
    'glossary.md', 'compliance-reference-map.md', 'tools/validate-artifacts.ps1',
    'tools/validate-artifacts.sh', 'tools/validate_artifacts.py', 'tools/scaffold_project.py',
    'tools/validate-installed-assurance.ps1', 'tools/validate-installed-assurance.sh', 'tools/validate_installed_assurance.py',
    'schemas/assurance-system-manifest.schema.json', 'examples/assurance-system-manifest.valid.json', 'examples/assurance-system-manifest.invalid.json',
    'process-contract.template.json', 'schemas/process-contract.schema.json', 'schemas/run-manifest.schema.json',
    'VERSION', 'schemas/verifier-config.schema.json', 'schemas/migration-record.schema.json', 'tools/run_verifier.py',
    'tools/verify-entrypoint.sh', 'tools/verify-entrypoint.ps1', 'tools/test_scaffold_project.py',
    'tools/assurance_gate.py', 'tools/test_assurance_gate.py', 'schemas/gate-result.schema.json', 'schemas/gate-baseline.schema.json',
    'adapters/github/assurance-gate.yml', 'adapters/gitlab/assurance-gate.gitlab-ci.yml', 'adapters/gitlab/gitlab_mr.py'
)
$missingRequired = @($requiredFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $rootPath $_)) })
Add-Check 'required-artifacts-present' ($missingRequired.Count -eq 0) $(if ($missingRequired.Count -eq 0) { 'All required top-level artifacts are present.' } else { $missingRequired -join ', ' })

$reportFullPath = [IO.Path]::GetFullPath($ReportPath)
$defaultReportFullPath = [IO.Path]::GetFullPath((Join-Path $rootPath 'validation-report.json'))
$fileInventory = Get-ChildItem -LiteralPath $rootPath -File -Recurse | Where-Object { $_.FullName -notin @($reportFullPath, $defaultReportFullPath) } | Sort-Object FullName | ForEach-Object {
    [ordered]@{
        path = [IO.Path]::GetRelativePath($rootPath, $_.FullName).Replace('\', '/')
        size_bytes = $_.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
}

$report = [ordered]@{
    schema_version = '1.0.0'
    generated_at = [DateTimeOffset]::UtcNow.ToString('o')
    validator = 'tools/validate-artifacts.ps1'
    powershell = $PSVersionTable.PSVersion.ToString()
    root = $rootPath
    status = if ($script:Failures.Count -eq 0) { 'pass' } else { 'fail' }
    checks = $script:Checks
    failures = $script:Failures
    limitations = @(
        'PowerShell Test-Json validates instances against Draft-07 schemas; this tool does not perform an online meta-schema fetch.',
        'External HTTP links are recorded but not fetched by this offline validator.',
        'Relative-link checking excludes project-start-here.template.md and project-readme.template.md because their links resolve only after repository relocation.',
        'The distribution check confirms architecture-template sections and diagram-as-code examples but does not parse or render Mermaid; each adopter must pin and run its declared renderer.',
        'Semantic checks cover declared cross-field invariants but do not prove evidence truth, identity ownership, signature cryptography, or compliance.'
    )
    files = @($fileInventory)
}

$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $reportFullPath -Encoding utf8NoBOM

if ($script:Failures.Count -gt 0) {
    $script:Failures | ForEach-Object { Write-Error $_ -ErrorAction Continue }
    exit 1
}

Write-Host "PASS: $($script:Checks.Count) checks; report: $reportFullPath"
