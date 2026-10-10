ESC = {}
ESC.ModuleUUID = '6560ea02-fe1e-5fdb-8631-b41a2e53af90'
ESC.Rules = Ext.Require('Rules.lua')
ESC.Engine = Ext.Require('Engine.lua')
Ext.Require('Runtime.lua')
Ext.Require('XueyanEchoVfx.lua').Install(ESC.Engine,Ext.Json.Parse(Ext.IO.LoadFile('Mods/EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90/ScriptExtender/Lua/GeneratedSpec.json','data')))
