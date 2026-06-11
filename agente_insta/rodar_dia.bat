@echo off
cd /d "C:\Users\Igor Hanate\Desktop\EvolutionFitIA"
if not exist "agente_insta\brief_aqui" mkdir "agente_insta\brief_aqui"
"C:\Users\Igor Hanate\AppData\Local\Programs\Python\Python312\python.exe" -m agente_insta.rodar_dia >> "agente_insta\brief_aqui\agente_insta_log.txt" 2>&1
