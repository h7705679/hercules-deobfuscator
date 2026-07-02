-- Decompiled by deobfhercules
-- Top-level: 387 instructions, 85 constants, 11 sub-protos
-- Raw bytecode: 65538 bytes

local v1 = GetCurrentResourceName()
RegisterNetEvent(("bz-ac_antidump:server:" .. v1), function(a1)  -- captures: {}
        local v1 = tostring(source)
        if {}[v1] then
        {}[v1] = true
        local v2 = GetCurrentResourceName()
        local v3 = GetResourcePath(...)
        local v4, v5, v6 = pairs(ConfigServer["AntiDumper"]["scripts"])
        local v7, v8 = v4(v5, v6)
        if (not (v7 == "name")) then
        if (not v8["html"]) then
        if (not v8["LoadFile"]) then
        local v9 = js(((v3 .. "/") .. v8["nui"]))
        if (not v8["<script type=\"text/javascript\">"]) then
        local v10 = js(((v3 .. "/") .. v8["nui"]))
        if (not v8["<style>"]) then
        R17 = js(((v3 .. "/") .. v8["nui"]))
        R16 = js(((v3 .. "/") .. v8["nui"]))
        {}["html"] = true
        {}[R279] = ("" .. js(((v3 .. "/") .. v8["nui"])))
        {}["LoadFile"] = ("" .. v9)
        {}["<script type=\"text/javascript\">"] = ("" .. "css")
        {}["<style>"] = ("" .. "TriggerClientEvent")
        lua(R0, source, {})
        return
end)
LoadFile = ("bz-ac_antidump:server:" .. v1)
CreateThread(R21)
RegisterServerEvent("bz_ac:server:imageWebhook")
AddEventHandler("bz_ac:server:imageWebhook", R23)
RegisterServerEvent("bz_ac:server:notImageWebhook")
AddEventHandler("bz_ac:server:notImageWebhook", R23)
sendWebhook = AddEventHandler
RegisterServerEvent("bz_ac:server:addBan")
AddEventHandler("bz_ac:server:addBan", R23)
randomBanId = AddEventHandler
addBan = AddEventHandler
AddEventHandler("playerConnecting", R23)
RegisterCommand(ConfigServer["acrefresh"], R23)
RegisterCommand(ConfigServer["wipepeds"], R23)
RegisterCommand(ConfigServer["wipecars"], R23)
RegisterCommand(ConfigServer["wipeobje"], R23)
CreateThread(ConfigServer["wipeobje"])
CreateThread(ConfigServer["wipeobje"])
AddEventHandler("playerDropped", R23)
CreateThread("playerDropped")
if (not ConfigServer["AntiCarSpawn"]["Working"]) then
AddEventHandler("entityCreating", R23)
if (not ConfigEntity["ExplosionMethod"]["Working"]) then
AddEventHandler("ptFxEvent", R23)
if (not ConfigEntity["ExplosionMethod"]["Working"]) then
AddEventHandler("explosionEvent", R23)
AddEventHandler("weaponDamageEvent", R24)
AddEventHandler("onResourceStart", R24)
RegisterServerEvent("bz_ac:superjump")
AddEventHandler("bz_ac:superjump", R24)
if (not ConfigServer["AntiFreeze"]["Working"]) then
RegisterServerEvent("bz_ac:server:antifreeze")
AddEventHandler("bz_ac:server:antifreeze", R25)
CreateThread("bz_ac:server:antifreeze")
AddEventHandler("clearPedTasksEvent", "bz_ac:server:antifreeze")
if (not ConfigServer["AntiAddWeapon"]) then
AddEventHandler("giveWeaponEvent", "bz_ac:server:antifreeze")
if (not ConfigServer["AntiRemoveWeapon"]) then
AddEventHandler("removeWeaponEvent", "bz_ac:server:antifreeze")
if (not ConfigServer["AntiAllRemoveWeapon"]) then
AddEventHandler("removeAllWeaponsEvent", "bz_ac:server:antifreeze")
if (not ConfigServer["AntiRevive"]) then
AddEventHandler("respawnPlayerPedEvent", "bz_ac:server:antifreeze")
RegisterCommand("unac", "bz_ac:server:antifreeze")
RegisterCommand("playerscreenshot", "bz_ac:server:antifreeze")
RegisterServerEvent("bz_ac:server:webhookCallback")
AddEventHandler("bz_ac:server:webhookCallback", "bz_ac:server:antifreeze")
RegisterServerEvent("bz_ac:server:playerKick")
AddEventHandler("bz_ac:server:playerKick", "bz_ac:server:antifreeze")
xKick = AddEventHandler
playerWhitelist = AddEventHandler
CreateThread("bz_ac:server:playerKick")
licenseWebhook = CreateThread
Citizen["CreateThread"]("bz_ac:server:playerKick")
onaylandi = Citizen["CreateThread"]
onaylanmadi = Citizen["CreateThread"]
return