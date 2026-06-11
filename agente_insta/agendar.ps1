$bat = Join-Path $PSScriptRoot "rodar_dia.bat"
$action = New-ScheduledTaskAction -Execute $bat
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "EvolutionFit Briefs" -Action $action -Trigger $trigger -Settings $settings -Description "Gera os briefs diarios da Evolution Fit" -Force | Out-Null
Write-Output "OK: tarefa 'EvolutionFit Briefs' criada para rodar todo dia as 02:00."
Start-ScheduledTask -TaskName "EvolutionFit Briefs"
Write-Output "Teste disparado agora. Veja a pasta brief_aqui em ~1 minuto."
