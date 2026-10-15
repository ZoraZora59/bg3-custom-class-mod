-- Server bridge: native spells own targeting/dice/saves; this file owns clocks,
-- source-specific rewards, snapshots and final damage. See runtime contract report.
local R,E=ESC.Rules,ESC.Engine
local spec=Ext.Json.Parse(Ext.IO.LoadFile('Mods/EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90/ScriptExtender/Lua/GeneratedSpec.json','data'))
E.resource,E.classes=spec.resource,spec.classes
local Rain=Ext.Require('TaixuanRainVfx.lua').New(E,spec.taixuanWorldRainVfx)
local CastVfx=Ext.Require('TianqingCastVfx.lua').New(E,spec.tianqingVfx,spec.schoolPolishVfx)
local Runtime={}
local keys,aliases={},spec.aliases or {}
for key,row in pairs(spec.spells) do keys[row.stat]=key end
for spell,alias in pairs(aliases) do keys[spell]=alias.key end
local helpers={internal_taiqing_pulse='Target_ESC_TaiqingPulse',internal_blood_pulse='Target_ESC_BloodPulse',
    internal_counter2='Target_ESC_Counter2',internal_counter3='Target_ESC_Counter3',
    internal_resonance='Target_ESC_Resonance',internal_aftershock='Target_ESC_Aftershock',
    internal_tiandi_stage='Target_ESC_TiandiStage',internal_tiandi_stage_nocontrol='Target_ESC_TiandiStage_NoControl',internal_tianbeng_main='Target_ESC_TianbengMain',
    internal_chengfeng_burst='Target_ESC_ChengfengBurst',internal_huifeng_control='Target_ESC_HuifengControl',
    internal_liuguang_stage='Target_ESC_LiuguangStage',internal_tianbeng_cone='Target_ESC_TianbengCone',
    internal_yixiantian_hit='Target_ESC_YixiantianHit'}
for key,spell in pairs(helpers) do keys[spell]=key end
E.classSpellKeys=keys
local basicSwordAttacks={Target_MainHandAttack=true,Target_OffHandAttack=true,
    Projectile_MainHandAttack=true,Projectile_OffHandAttack=true,
    Target_OffhandAttack=true,Projectile_OffhandAttack=true}
local watched,casts,contexts,pendingHelpers,stages={}, {}, {}, {}, {}
local retiredFailures,retiredFailureOrder={},{}
local syncFollowupBoostAliases
local tiandiDispatch
local Line={}
local auraTargets,sequence,timerGeneration={},0,0
local pendingSessionLoad=0
local auraVisualTargets={}
local pendingDomainTurnPulses={}
local domainStatuses={taixuan_taiqing='ESC_SWORD_DOMAIN',xueyan_xuehai='ESC_BLOOD_ROBE',
    tianqing_tianjian='ESC_TIANQING_AFTERSHOCK',xingge_fengyu='ESC_DAMAGE_SHARE',xingge_zhangjian='ESC_TEAM_RESONANCE'}
local domainKeys={}
for key,status in pairs(domainStatuses) do domainKeys[status]=key end
local rescueRequests={}
local cooperationRequests={}
local pendingAvatarRefreshes={}
local pendingWeaponWisdom={}
local tianqingTimerHandles={}
local healingContexts={}
local nativeHeals,nativeHealOrder,pendingWindHealing={},{},{}
local function nativeHealKey(source,target,action)
    if not source or not target or type(action)~='number' or action<=0 then return nil end
    return source..':'..target..':'..tostring(action)
end
local function healingInterference(target,exceptKey)
    target=E.uuid(E.entity(target))
    for key,receipt in pairs(nativeHeals) do
        if key~=exceptKey and receipt.target==target then receipt.ambiguous=true end
    end
end
-- Direct scripted healing already applies HealingMultiplier in Engine.heal.
-- It must not turn a waiting native heal's later net HP into false support.
Runtime.NotifyHealingInterference=healingInterference
local function rememberNativeHeal(source,target,action,spell)
    local key=nativeHealKey(source,target,action);if not key then return nil end
    healingInterference(target,key)
    local old=nativeHeals[key]
    if old then return old end
    local receipt={key=key,source=source,target=target,action=action,spell=spell,before=E.hp(target),maximum=E.maxHp(target)}
    nativeHeals[key]=receipt;nativeHealOrder[#nativeHealOrder+1]=receipt
    -- No timer or per-tick scan. Keep only a bounded set of unconsumed native
    -- actions; session reload clears it and native HEAL consumes each receipt.
    if #nativeHealOrder>128 then
        local expired=table.remove(nativeHealOrder,1)
        if nativeHeals[expired.key]==expired then nativeHeals[expired.key]=nil end
    end
    return receipt
end
local diagnostics={enabled=false,events={}}
local function trace(phase,row)
    if not diagnostics.enabled or #diagnostics.events>=1000 then return end
    row=row or {};row.phase=phase;row.sequence=#diagnostics.events+1
    diagnostics.events[#diagnostics.events+1]=row
end
local pendingTransfer
local bonusAction='420c8df5-45c2-4253-93c2-7ec44e127930'
local controls={RESTRAINED=true,ENTANGLED=true,HOLD_PERSON=true,HOLD_MONSTER=true,PRONE=true,
    STUNNED=true,PARALYZED=true,SLEEPING=true,SLEEP=true,FRIGHTENED=true,CHARMED=true,
    DOMINATED=true,BLINDED=true,SILENCED=true}
local critical={HOLD_PERSON=true,HOLD_MONSTER=true,STUNNED=true,PARALYZED=true,SLEEPING=true,SLEEP=true,
    CHARMED=true,DOMINATED=true}
local groups={SG_Restrained=true,SG_Prone=true,SG_Stunned=true,SG_Paralyzed=true,SG_Sleeping=true,
    SG_Frightened=true,SG_Charmed=true,SG_Dominated=true,SG_Blinded=true,SG_Silenced=true}
Ext.Vars.RegisterUserVariable('ESC_State',{Server=true,Client=false,Persistent=true})
-- A death receipt belongs to that victim's current life, not to an ever-growing
-- list on every blood cultivator. Resurrection retires it without any polling.
Ext.Vars.RegisterUserVariable('ESC_BloodKillReceipts',{Server=true,Client=false,Persistent=true})
local function migrateKills(owner,s)
    if not next(s.kills or {}) then return false end
    for target in pairs(s.kills) do
        local entity=E.entity(target)
        if entity and E.character(target) and (not E.alive(target) or E.hp(target)<=0) then
            local receipts=entity.Vars.ESC_BloodKillReceipts or {}
            if not receipts[owner] then receipts[owner]=true;entity.Vars.ESC_BloodKillReceipts=receipts end
        end
    end
    s.kills={}
    return true
end
local function retainedState(id,s)
    if E.class(id)>0 then return true end
    if not E.character(id) or not s then return false end
    for _,key in ipairs({'marks','protections','debuffs','domains','chains'}) do
        if next(s[key] or {}) then return true end
    end
    for _,value in pairs(s.boosts or {}) do if value and value~='' then return true end end
    return s.guard~=nil or (s.shield or 0)>0
end
local function needsPeriodic(id,s)
    if E.class(id)>0 then return true end
    if not E.character(id) or not s then return false end
    for _,key in ipairs({'marks','protections','debuffs','domains','chains'}) do
        if next(s[key] or {}) then return true end
    end
    return false
end
local function state(id)
    local entity=E.entity(id)
    if not entity then return nil end
    id=E.uuid(entity) or id
    local s=entity.Vars.ESC_State
    local created=s==nil;s=s or {qiSword=false}
    local changed=created
    for key,value in pairs({turn=0,frenzy=0,shield=0,damageMode='Necrotic'}) do
        if s[key]==nil then s[key]=value;changed=true end
    end
    for _,key in ipairs({'marks','protections','domains','kills','boosts','chains','debuffs'}) do
        if s[key]==nil then s[key]={};changed=true end
    end
    if migrateKills(id,s) then changed=true end
    if retainedState(id,s) then
        watched[id]=needsPeriodic(id,s) or nil
        if changed then entity.Vars.ESC_State=s end
    end
    -- Ordinary damage/turn callbacks still get neutral rule defaults, but merely
    -- reading them must not attach persistent state or enroll unrelated actors.
    return s
end
local function retireEmptyState(id,s)
    local entity=E.entity(id);if not entity then return end
    id=E.uuid(entity) or id
    if retainedState(id,s) then watched[id]=needsPeriodic(id,s) or nil;return end
    watched[id]=nil
    if entity.Vars.ESC_State~=nil then entity.Vars.ESC_State=nil end
end
local function save(id,s)
    local entity=E.entity(id);if not entity then return end
    id=E.uuid(entity) or id
    if retainedState(id,s) then watched[id]=needsPeriodic(id,s) or nil;entity.Vars.ESC_State=s
    else retireEmptyState(id,s) end
end
-- Preserve the explicit public State accessor used by integrations and console
-- tooling to attach a real state before editing it. Internal reads stay neutral.
local function explicitState(id)
    local s=state(id);local entity=s and E.entity(id)
    if entity and syncFollowupBoostAliases then syncFollowupBoostAliases(id) end
    if entity and entity.Vars.ESC_State==nil then entity.Vars.ESC_State=s end
    if entity then watched[E.uuid(entity) or id]=true end
    return s
end
-- Resolve through the entity: story names and ECS UUIDs are aliases, not two
-- actors. Keep this local to party mechanics; unrelated persisted maps retain
-- their existing keys and clocks.
local function actorId(id) return E.uuid(E.entity(id)) or id end
local function watchedActors()
    local actors={}
    for id in pairs(watched) do
        local uuid=E.uuid(E.entity(id));if uuid then actors[uuid]=true end
    end
    return actors
end
local function actorUses(used)
    local canonical={}
    for id,value in pairs(used or {}) do
        if value then canonical[actorId(id)]=value end
    end
    return canonical
end
local function markKeys(s,kind,owner)
    local found={};local prefix=kind..':'
    for key in pairs(s.marks) do
        if key:sub(1,#prefix)==prefix and E.sameEntity(key:sub(#prefix+1),owner) then found[#found+1]=key end
    end
    return found
end
local function followupBoost(owner)
    return "IF(HasStatus('ESC_FOLLOWUP',context.Target,'"..owner.."')):RollBonus(Attack,2)"
end
syncFollowupBoostAliases=function(id)
    local s=state(id);local stale,owners={},{}
    for slot,boost in pairs(s.boosts) do
        if slot:sub(1,9)=='followup_' and boost~='' then
            local old=slot:sub(10);local owner=E.uuid(E.entity(old))
            if E.sameEntity(old,id) then stale[#stale+1]=slot
            elseif owner and old~=owner then stale[#stale+1]=slot;owners[owner]=true end
        end
    end
    -- Old self slots must disappear; only allies retain a canonical bonus.
    -- Other old save slots can otherwise stack with that slot on recast.
    for _,slot in ipairs(stale) do E.setBoosts(id,slot,'') end
    for owner in pairs(owners) do E.setBoosts(id,'followup_'..owner,followupBoost(owner)) end
end
-- The engine status is the sole duration clock, both in and out of combat.
-- Persisted turn counters remain a snapshot only; they must not revive expired DR.
local guardValues={{rank=1,ac=2,reduction=.2},{rank=2,ac=3,reduction=.3,dice='4d8',attack=2},
    {rank=3,ac=5,reduction=.4,dice='6d8',attack=3}}
local function syncGuard(id,reapplied)
    local s=state(id);if not s then return end
    if not E.hasStatus(id,'ESC_COUNTER_READY') then s.guard=nil
    else
        local rank=E.hasStatus(id,'ESC_COUNTER_RANK3') and 3 or E.hasStatus(id,'ESC_COUNTER_RANK2') and 2 or 1
        if reapplied or not s.guard or s.guard.rank~=rank then s.guard=R.guard(nil,guardValues[rank],s.turn) end
    end
    save(id,s);return s
end
local function keyFor(spell) return keys[E.spellName(spell)] end
local function offensiveKey(key)
    local row=key and spec.spells[key]
    return row and row.base and row.base~='' or key=='internal_taiqing_pulse' or key=='internal_blood_pulse'
        or key=='internal_counter2' or key=='internal_counter3' or key=='internal_resonance'
        or key=='internal_aftershock' or key=='internal_tiandi_stage' or key=='internal_tiandi_stage_nocontrol' or key=='internal_tianbeng_main'
        or key=='internal_chengfeng_burst' or key=='internal_liuguang_stage' or key=='internal_tianbeng_cone' or key=='internal_yixiantian_hit'
end
local function validDomain(id,key)
    local s=state(id);local d=s and s.domains[key]
    local _,branch=E.class(id)
    return d and R.tickDuration(d,s.turn) and E.alive(id) and E.allowed(id,branch,false) and d or nil
end
local function endDomain(id,key)
    local s=state(id)
    if not s or not s.domains[key] then return end
    s.domains[key]=nil;save(id,s)
    local pending=pendingDomainTurnPulses[E.uuid(E.entity(id)) or id]
    if pending then pending[key]=nil end
end
local function activeMark(target,kind,owner)
    if not E.character(target) then return nil end
    owner=actorId(owner)
    local s,source=state(target),state(owner);if not s or not source then return nil end
    local mark,used,oldKeys=nil,{},markKeys(s,kind,owner)
    -- Preserve pre-upgrade names and their consumed allowances. Merging active
    -- aliases neither restarts the duration nor grants another response.
    for _,key in ipairs(oldKeys) do
        local entry=s.marks[key]
        if source.turn<entry.expires then
            if not mark or entry.expires>mark.expires then mark=entry end
            for id,value in pairs(actorUses(entry.used)) do used[id]=value end
        end
    end
    for _,key in ipairs(oldKeys) do s.marks[key]=nil end
    if mark then mark.used=used;s.marks[kind..':'..owner]=mark end
    save(target,s);return mark
end
local function isControlled(status)
    if type(status)~='string' or status=='' then return false end
    if controls[status] then return true end
    local stat=Ext.Stats.Get(status,nil,false);if not stat then return false end
    local rows=stat.StatusGroups
    if type(rows)=='string' then
        for group in pairs(groups) do if rows:find(group,1,true) then return true end end
    elseif rows then for _,group in pairs(rows) do if groups[group] then return true end end end
    return false
end
local function controlStatusName(status)
    -- The ECS StatusContainer maps entity handles to FixedString names, unlike
    -- legacy StatusManager arrays which contain status objects.
    if type(status)=='string' then return status end
    if type(status)=='table' then return status.StatusId or status.StatusID end
end
local function clearControls(target,source)
    local entity=E.entity(target);if not entity then return false end
    local names={}
    for _,status in pairs(entity.StatusContainer and entity.StatusContainer.Statuses or {}) do
        local name=controlStatusName(status);if isControlled(name) then names[name]=true end
    end
    for name in pairs(controls) do if E.hasStatus(target,name) then names[name]=true end end
    for name in pairs(names) do E.removeStatus(target,name,source) end
    return next(names)~=nil
end
local function hasControls(id)
    local entity=E.entity(id)
    for _,status in pairs(entity and entity.StatusContainer and entity.StatusContainer.Statuses or {}) do
        if isControlled(controlStatusName(status)) then return true end
    end
    for status in pairs(controls) do if E.hasStatus(id,status) then return true end end
    return false
end
local function updateRescue(id)
    local level,branch=E.class(id)
    local available=E.alive(id) and E.allowed(id,branch,false) and (branch=='xingge' and level>=8 or branch~='xingge' and level>=5) and hasControls(id)
    local entry=rescueRequests[id]
    if available and not entry then
        sequence=sequence+1;entry={token=sequence};rescueRequests[id]=entry
        if Ext.ServerNet then Ext.ServerNet.PostMessageToClient(id,'ESC_ControlRescueState',Ext.Json.Stringify({id=id,available=true,token=entry.token})) end
    elseif not available and entry then
        rescueRequests[id]=nil
        if Ext.ServerNet then Ext.ServerNet.PostMessageToClient(id,'ESC_ControlRescueState',Ext.Json.Stringify({id=id,available=false})) end
    end
end
local function rescue(id,token,peer)
    local request=rescueRequests[id]
    if not request or request.token~=token or type(peer)~='number' then return false end
    local user=(peer & 0xffff0000) | 0x0001
    if Osi.GetReservedUserID(id)~=user then return false end
    local level,branch=E.class(id)
    if not E.alive(id) or not E.allowed(id,branch,false) or not hasControls(id) or (branch=='xingge' and level<8 or branch~='xingge' and level<5) then return false end
    local entity=E.entity(id)
    if E.combat(id) and (not entity.TurnBased or not entity.TurnBased.IsActiveCombatTurn) then return false end
    local yuan=E.resourceEntry(id,E.resource);local bonus=E.resourceEntry(id,bonusAction)
    if not yuan or yuan.Amount<4 or not bonus or bonus.Amount<1 then return false end
    E.spendResource(id,E.resource,4);E.spendResource(id,bonusAction,1)
    clearControls(id,id);E.status(id,'ESC_CONTROL_RESISTANCE',2,id);updateRescue(id);return true
end
local function sendCooperation(id)
    id=actorId(id)
    local request=cooperationRequests[id] and cooperationRequests[id][1]
    -- An assigned companion can have no active ServerCharacter.UserID, which
    -- makes PostMessageToClient reject it. Resolve its current controller via
    -- the same native query used to authenticate the later choice; never cache
    -- a volatile user ID or substitute the host for an unassigned character.
    local user=Osi.GetReservedUserID(id)
    if Ext.ServerNet and type(user)=='number' and user~=-65536 and user~=0xffff0000 then
        Ext.ServerNet.PostMessageToUser(user,'ESC_CooperationState',Ext.Json.Stringify(request and {
            id=id,available=true,token=request.token,options=E.freeOptions(id,request.target)} or {id=id,available=false}))
    end
end
local function requestCooperation(id,owner,target,action)
    id,owner,target=actorId(id),actorId(owner),actorId(target)
    local options=E.freeOptions(id,target);if #options==0 then return false end
    sequence=sequence+1
    cooperationRequests[id]=cooperationRequests[id] or {}
    cooperationRequests[id][#cooperationRequests[id]+1]={token=sequence,owner=owner,target=target,action=action,turn=state(owner).turn}
    if #cooperationRequests[id]==1 then sendCooperation(id) end
    return true
end
local function chooseCooperation(id,token,spell,peer)
    id=actorId(id)
    local queue=cooperationRequests[id];local request=queue and queue[1]
    if not request or request.token~=token or type(peer)~='number' then return false end
    if Osi.GetReservedUserID(id)~=((peer & 0xffff0000) | 0x0001) then return false end
    if not E.friend(request.owner,id) or not E.alive(request.owner) or not E.enemy(request.owner,request.target)
        or state(request.owner).turn~=request.turn then return false end
    if spell=='decline' then table.remove(queue,1);sendCooperation(id);return true end
    local eligible=false
    for _,option in ipairs(E.freeOptions(id,request.target)) do if option.spell==spell then eligible=true;break end end
    if not eligible then return false end
    pendingHelpers[id]=pendingHelpers[id] or {}
    pendingHelpers[id][#pendingHelpers[id]+1]={key=nil,meta={cooperator=request.owner,parent=request.action,originalSpell=spell},target=request.target}
    if not E.freeAttack(id,request.target,spell) then table.remove(pendingHelpers[id]);return false end
    table.remove(queue,1);sendCooperation(id);return true
end
local function spellConditions(automaticOnly,offhandOnly)
    -- GST strings have a 2048-byte limit. Split the complete boosts, not merely
    -- the conditions: attack + DC repeat each condition in the same string.
    local tests={}
    for spell,key in pairs(keys) do
        local row=spec.spells[key]
        local alias=aliases[spell] or {};local parent=alias.parent and spec.spells[alias.parent]
        local automatic=row and row.base=='AUTO' or parent and parent.base=='AUTO' or alias.hand=='auto'
        local fixedOff=alias.bonusOnly and alias.offhand or false
        if automaticOnly and automatic and fixedOff==(offhandOnly or false) or not automaticOnly and (row and row.base and row.base~='' or key:find('internal_',1,true)==1) then
            tests[#tests+1]="SpellId('"..spell.."')"
        end
    end
    table.sort(tests)
    local chunks,current={},''
    for _,test in ipairs(tests) do
        if #current+#test+4>700 then chunks[#chunks+1]='('..current..')';current='' end
        current=current=='' and test or current..' or '..test
    end
    if current~='' then chunks[#chunks+1]='('..current..')' end
    return chunks
end
local spellOnly,automaticOnly,automaticOffhand=spellConditions(),spellConditions(true),spellConditions(true,true)
local function scopedBoosts(id,prefix,attack,dc,conditions)
    for i,condition in ipairs(conditions or spellOnly) do
        local value={}
        if attack and attack~=0 then value[#value+1]='IF('..condition..'):RollBonus(Attack,'..attack..')' end
        if dc and dc~=0 then value[#value+1]='IF('..condition..'):SpellSaveDC('..dc..')' end
        E.setBoosts(id,prefix..i,table.concat(value,';'))
    end
end
local function controlBoost(id,bonus,advantage)
    local covered={};for name in pairs(controls) do covered[name]=true end
    if Ext.Stats.GetStats then for _,name in ipairs(Ext.Stats.GetStats('StatusData')) do if isControlled(name) then covered[name]=true end end end
    local names={};for name in pairs(covered) do names[#names+1]=name end;table.sort(names)
    local parts,chunks={},{}
    local length=0
    for _,name in ipairs(names) do
        local part="StatusId('"..name.."')"
        if length+#part+4>700 then chunks[#chunks+1]=table.concat(parts,' or ');parts={};length=0 end
        parts[#parts+1]=part;length=length+#part+4
    end
    if #parts>0 then chunks[#chunks+1]=table.concat(parts,' or ') end
    local result={}
    for _,condition in ipairs(chunks) do
        local gate='IF('..condition..'):'
        result[#result+1]=gate..'RollBonus(SavingThrow,'..bonus..')'..(advantage and ';'..gate..'Advantage(AllSavingThrows)' or '')
    end
    return result
end
local function syncReceivedControlResistance(id)
    -- A party member need not have the sword class to receive Fuchen's native
    -- saving-throw boosts. The native status, including its expiry, is authority.
    local s=state(id);if not s then return end
    local wanted={}
    if E.hasStatus(id,'ESC_CONTROL_RESISTANCE') then
        for i,value in ipairs(controlBoost(id,2,false)) do
            local slot='control_save_'..i;wanted[slot]=true;E.setBoosts(id,slot,value)
        end
    end
    for slot in pairs(s.boosts) do
        if slot:find('control_save_',1,true)==1 and not wanted[slot] then E.setBoosts(id,slot,'') end
    end
end
local function weaponWisdom(id,s,allowed)
    local wanted,checked={},{};local owner=E.uuid(E.entity(id)) or id;local cause='ESC_WEAPON_WISDOM_'..owner
    for _,off in ipairs({false,true}) do
        local sword=E.sword(id,off);local _,normal=E.swordAttribute(id,off)
        if sword then checked[sword]=true end
        if allowed and sword and E.ability(id,'Wisdom')>normal then wanted[sword]=true end
    end
    for sword in pairs(s.weaponWisdom or {}) do checked[sword]=true end
    for sword in pairs(checked) do
        if not wanted[sword] and E.entity(sword) then
            local ownCauses=E.weaponWisdomCauses(sword,owner)
            local pendingKey=cause..'|'..sword
            if pendingWeaponWisdom[pendingKey] then ownCauses[#ownCauses+1]=cause;pendingWeaponWisdom[pendingKey]=nil end
            for _,ownCause in ipairs(ownCauses) do Osi.RemoveBoosts(sword,'WeaponAttackRollAbilityOverride(Wisdom)',0,ownCause,id) end
        end
    end
    for sword in pairs(wanted) do
        -- An absent boost needs only AddBoosts: native removal is deferred and
        -- a remove/add pair can erase the replacement during the same update.
        -- Share one pending add across Name_GUID/GUID callbacks until next tick.
        local pendingKey=cause..'|'..sword
        if not E.hasWeaponWisdom(sword,cause) and not pendingWeaponWisdom[pendingKey] then
            local pending={};pendingWeaponWisdom[pendingKey]=pending
            Osi.AddBoosts(sword,'WeaponAttackRollAbilityOverride(Wisdom)',cause,id)
            Ext.OnNextTick(function() if pendingWeaponWisdom[pendingKey]==pending then pendingWeaponWisdom[pendingKey]=nil end end)
        end
    end
    local current=state(id);current.weaponWisdom=wanted;save(id,current)
    -- Vanilla SHILLELAGH / PactWeapon apply this override to the actual weapon.
    -- An actor override would affect unrelated weapons and both hands together.
    E.setBoosts(id,'wisdom','')
end
local legacyStartingSpells={'Shout_ESC_StartingSword','Shout_ESC_StartingSword_longsword',
    'Shout_ESC_StartingSword_greatsword','Shout_ESC_StartingSword_dualshorts'}
local mergedOffhandContainers={'Shout_ESC_Offhand_taixuan_zhaoxi','Shout_ESC_Offhand_tianqing_nifeng',
    'Shout_ESC_Offhand_xueyan_luexue','Shout_ESC_Offhand_xingge_wenlu'}
local legacyUnifiedSwordSpells={
    'Projectile_ESC_yujian_Main',
    'Projectile_ESC_yujian_Off',
    'Target_ESC_sword_strike_Main',
    'Target_ESC_sword_strike_Off',
    'Target_ESC_taixuan_zhaoxi_MeleeMain',
    'Target_ESC_taixuan_zhaoxi_MeleeOff',
    'Target_ESC_taixuan_zhaoxi_MeleeOff_Bonus',
    'Projectile_ESC_taixuan_zhaoxi_RangedMain',
    'Projectile_ESC_taixuan_zhaoxi_RangedOff',
    'Zone_ESC_tianqing_nifeng_MeleeMain',
    'Zone_ESC_tianqing_nifeng_MeleeOff',
    'Zone_ESC_tianqing_nifeng_MeleeOff_Bonus',
    'Zone_ESC_tianqing_nifeng_RangedMain',
    'Zone_ESC_tianqing_nifeng_RangedOff',
    'Target_ESC_tianqing_wanjun_Main',
    'Target_ESC_tianqing_wanjun_Off',
    'Target_ESC_tianqing_lietian_Main',
    'Target_ESC_tianqing_lietian_Off',
    'Target_ESC_tianqing_tianbeng_Main',
    'Target_ESC_tianqing_tianbeng_Off',
    'Rush_ESC_tianqing_tianfeng_Main',
    'Rush_ESC_tianqing_tianfeng_Off',
    'Projectile_ESC_tianqing_tianjian_Main',
    'Projectile_ESC_tianqing_tianjian_Off',
    'Shout_ESC_tianqing_bafang_Main',
    'Shout_ESC_tianqing_bafang_Off',
    'Target_ESC_tianqing_tiandi_Main',
    'Target_ESC_tianqing_tiandi_Off',
    'Target_ESC_xueyan_luexue_MeleeMain',
    'Target_ESC_xueyan_luexue_MeleeOff',
    'Target_ESC_xueyan_luexue_MeleeOff_Bonus',
    'Projectile_ESC_xueyan_luexue_RangedMain',
    'Projectile_ESC_xueyan_luexue_RangedOff',
    'Rush_ESC_xueyan_chuanshen_Main',
    'Rush_ESC_xueyan_chuanshen_Off',
    'Target_ESC_xingge_wenlu_MeleeMain',
    'Target_ESC_xingge_wenlu_MeleeOff',
    'Target_ESC_xingge_wenlu_MeleeOff_Bonus',
    'Projectile_ESC_xingge_wenlu_RangedMain',
    'Projectile_ESC_xingge_wenlu_RangedOff',
    'Target_ESC_xingge_chengfeng_Main',
    'Target_ESC_xingge_chengfeng_Off',
    'Projectile_ESC_xingge_tongzhou_Main',
    'Projectile_ESC_xingge_tongzhou_Off',
    'Target_ESC_liancheng_ContinueMelee',
    'Target_ESC_wusheng_ContinueMelee',
}
local function removeKnownSpell(id,spell,removeChildren)
    if Osi.HasSpell(id,spell)==1 then Osi.RemoveSpell(id,spell,removeChildren) end
end
local function removeKnownPassive(id,passive)
    if Osi.HasPassive(id,passive)==1 then Osi.RemovePassive(id,passive) end
end
local function clearContinuous(id)
    local pool=E.resourceEntry(id,spec.opportunityResource)
    if pool and pool.Amount~=0 then pool.Amount=0;E.entity(id):Replicate('ActionResources') end
    for _,status in ipairs({'ESC_EXTRA_ATTACK',table.unpack(spec.opportunityStatuses or {})}) do
        if E.hasStatus(id,status) then E.removeStatus(id,status,id) end
    end
end
local function syncContinuous(id,level,branch)
    local s=state(id)
    if level<5 then
        clearContinuous(id)
        if s.nativeContinuous then
            for _,passive in ipairs(spec.continuousPassives or {}) do removeKnownPassive(id,passive) end
        end
        return
    end
    -- Add native trigger shards to older characters whose saved progression
    -- predates them. Never replenish the pool from a Lua cast callback.
    if s.nativeContinuous~=1 then clearContinuous(id);s.nativeContinuous=1;save(id,s) end
    for _,passive in ipairs(spec.continuousPassives or {}) do
        if Osi.HasPassive(id,passive)~=1 then Osi.AddPassive(id,passive) end
    end
    -- Native OnCast can grant the pool before ESC_EXTRA_ATTACK becomes active.
    -- Guard status callbacks also refresh in that window; absence of the status
    -- is not proof of a stale pool. The status owns continuation permissions.
    -- Explicit turn/leave/death callbacks still clear the pool, as do invalid
    -- equipment and the one-time migration above. Never grant charges in Lua.
    if not E.allowed(id,branch,false) or not E.alive(id) then clearContinuous(id) end
end
local function repairSavedBonusTechnique(id)
    local level,branch=E.class(id)
    if level<3 then return end
    local bonus=({taixuan='Projectile_ESC_taixuan_zhaoxi_RangedOff_Bonus',
        tianqing='Zone_ESC_tianqing_nifeng_RangedOff_Bonus',
        xueyan='Projectile_ESC_xueyan_luexue_RangedOff_Bonus',
        xingge='Projectile_ESC_xingge_wenlu_RangedOff_Bonus'})[branch]
    if bonus and Osi.HasSpell(id,bonus)~=1 then Osi.AddSpell(id,bonus,0,0) end
end
local function migrateSkillMenu(id,level,branch)
    -- Only current sword cultivators own this migration. Check each grant on
    -- refresh so old saves, levelling and respec all converge without a save flag.
    if level<=0 then return end
    for _,spell in ipairs(legacyStartingSpells) do removeKnownSpell(id,spell,1) end
    for _,spell in ipairs(legacyUnifiedSwordSpells) do removeKnownSpell(id,spell,0) end
    removeKnownSpell(id,'Target_ESC_sword_strike',0)
    removeKnownPassive(id,'ESC_P_StarterMelee')
    local oldLietian=Osi.HasSpell(id,'Projectile_ESC_tianqing_lietian')==1
    if oldLietian then
        removeKnownSpell(id,'Projectile_ESC_tianqing_lietian',0)
        local unlock=spec.spells.tianqing_lietian and spec.spells.tianqing_lietian.level
        if branch=='tianqing' and type(unlock)=='number' and level>=unlock and Osi.HasSpell(id,'Target_ESC_tianqing_lietian')~=1 then
            Osi.AddSpell(id,'Target_ESC_tianqing_lietian',0,1)
        end
    end
    -- Bonus leaves belong to native progression. Do not repair them here:
    -- equipment/status callbacks can run before a respec publishes its grants,
    -- producing an extra Osiris entry beside the later subclass entry.
    -- Only an already loaded old save needs repair (see sessionLoaded).
    -- Removing an old offhand parent must not remove retained bonus leaves.
    for _,spell in ipairs(mergedOffhandContainers) do removeKnownSpell(id,spell,0) end
    removeKnownSpell(id,'Shout_ESC_tianqing_xushi',0)
    -- Retired utility: clean an existing saved grant without replacing it.
    removeKnownSpell(id,'Target_ESC_recall_sword',0)
    removeKnownSpell(id,'Target_ESC_focus_target',0)
    removeKnownSpell(id,'Shout_ESC_qi_sword',0)
    if level>=3 then
        removeKnownPassive(id,'ESC_P_StarterSword')
        removeKnownPassive(id,'ESC_P_StarterMelee')
        for _,parent in ipairs({'Target_ESC_sword_strike','Projectile_ESC_yujian'}) do
            for _,suffix in ipairs({'','_Main','_Off'}) do removeKnownSpell(id,parent..suffix,0) end
        end
    end
    if branch=='taixuan' and level>=4 then
        removeKnownPassive(id,'ESC_P_StarterGuard')
        removeKnownSpell(id,'Shout_ESC_qi_guard',0)
    end
    if branch=='tianqing' and level>=6 then
        local old=false
        for _,suffix in ipairs({'','_Main','_Off'}) do
            local spell='Zone_ESC_tianqing_tianbeng'..suffix
            if Osi.HasSpell(id,spell)==1 then old=true;Osi.RemoveSpell(id,spell,0) end
        end
        -- Repair only an existing old grant. Native progression grants new
        -- characters the new targeted root without a runtime unlock.
        if old and Osi.HasSpell(id,'Target_ESC_tianqing_tianbeng')~=1 then
            Osi.AddSpell(id,'Target_ESC_tianqing_tianbeng',0,1)
        end
    end
end
local function syncChengfengBoosts(id,active,movement)
    -- Different lifetimes need distinct native SourceIDs. Replacing the old
    -- compound slot removes IgnoreLeaveAttackRange too; deferred removal can
    -- then erase the same-source replacement after its AddBoosts request.
    -- Retire that legacy source once, without reusing it for either new slot.
    E.setBoosts(id,'chengfeng','')
    E.setBoosts(id,'chengfeng_oa',active and 'IgnoreLeaveAttackRange()' or '')
    E.setBoosts(id,'chengfeng_movement',movement and 'ActionResource(Movement,6,0)' or '')
end
local function refresh(id)
    local level,branch=E.class(id)
    if level==0 and not watched[actorId(id)] then return end
    local s=syncGuard(id,false);if not s then return end
    -- Existing saves cannot retain the retired manual qi-sword mode.
    s.qiSword=false;save(id,s);E.removeStatus(id,'ESC_QI_MODE',id)
    syncContinuous(id,level,branch)
    if level==0 then
        removeKnownSpell(id,'Shout_ESC_qi_sword',0)
        weaponWisdom(id,s,false)
        -- Received party support is reconciled by updateAuras, independently of
        -- the beneficiary's class. A normal companion turn must not remove it.
        for slot in pairs(s.boosts) do
            if slot~='aura' and slot~='chengfeng' and slot~='chengfeng_oa' and slot~='chengfeng_movement'
                and slot:find('control_save_',1,true)~=1 then E.setBoosts(id,slot,'') end
        end
        syncReceivedControlResistance(id)
        s=state(id);s.frenzy=0;s.shield=0;s.domains={};s.guard=nil;s.chains={};save(id,s)
        for _,status in ipairs({'ESC_MAIN_SWORD','ESC_OFFHAND_SWORD','ESC_ARMOR_BLOCKED','ESC_COUNTER_READY','ESC_COUNTER_RANK2','ESC_COUNTER_RANK3','ESC_EXTRA_ATTACK','ESC_IN_FLIGHT','ESC_CHAIN_LIANCHENG','ESC_CHAIN_WUSHENG','ESC_VFX_SWORD_DOMAIN','ESC_VFX_BLOOD_DOMAIN'}) do E.removeStatus(id,status,id) end
        return
    end
    migrateSkillMenu(id,level,branch)
    local allowed=E.allowed(id,branch,false);local bonus=R.attackBonus(level,branch)
    for _,entry in ipairs({{'ESC_MAIN_SWORD',E.sword(id)~=nil},{'ESC_OFFHAND_SWORD',E.sword(id,true)~=nil},
        {'ESC_ARMOR_BLOCKED',not allowed and E.shield(id)==nil}}) do
        if entry[2] then
            if not E.hasStatus(id,entry[1]) then E.status(id,entry[1],-1,id) end
        else E.removeStatus(id,entry[1],id) end
    end
    local ac=level<3 and 0 or ({taixuan=level>=11 and 6 or 5,tianqing=1,xueyan=1,xingge=0})[branch] or 0
    -- Active guard AC belongs to ESC_COUNTER_READY; never add it twice here.
    if s.dashUntil and s.dashUntil>s.turn then ac=ac+2 end
    E.setBoosts(id,'combat',allowed and 'AC('..ac..')' or '')
    scopedBoosts(id,'sword_stats_',allowed and bonus or 0,allowed and bonus or 0)
    -- Immediate helpers can roll before UsingSpell. Equipment-only accuracy must
    -- already exist and must not be added again by BeginCast.
    local techniqueModifier=E.techniqueAttribute(id)
    local techniqueAdjustment=math.max(0,techniqueModifier-E.ability(id,'Wisdom'))
    scopedBoosts(id,'auto_weapon_accuracy_',allowed and techniqueAdjustment or 0,0,automaticOnly)
    local offhandModifier=E.techniqueAttribute(id,true)
    local offhandAdjustment=math.max(0,offhandModifier-E.ability(id,'Wisdom'))
    scopedBoosts(id,'auto_offhand_accuracy_',allowed and offhandAdjustment or 0,0,automaticOffhand)
    local weaponBoosts={}
    if allowed and E.sword(id) then weaponBoosts[#weaponBoosts+1]='RollBonus(MeleeWeaponAttack,'..bonus..')' end
    if allowed and E.sword(id,true) then weaponBoosts[#weaponBoosts+1]='RollBonus(MeleeOffHandWeaponAttack,'..bonus..')' end
    E.setBoosts(id,'weapon_stats',table.concat(weaponBoosts,';'))
    local extra=R.hitpoints(level,E.ability(id,'Constitution'),branch)-R.hitpoints(level,E.ability(id,'Constitution'),nil)
    E.setBoosts(id,'hp',extra>0 and 'IncreaseMaxHP('..extra..')' or '')
    weaponWisdom(id,s,allowed)
    -- Automatic techniques can select the off-hand sword with a non-sword or
    -- empty main hand. Its native weapon roll still needs its ability modifier.
    E.setBoosts(id,'two_swords',allowed and E.sword(id,true) and 'TwoWeaponFighting()' or '')
    local resistance=level>=3 and branch~='xingge' and allowed and 4 or 0
    local temporary=E.hasStatus(id,'ESC_CONTROL_RESISTANCE') and 2 or 0
    local controlValues=controlBoost(id,resistance+temporary,resistance>0)
    for i,value in ipairs(controlValues) do E.setBoosts(id,'control_save_'..i,(resistance+temporary)>0 and value or '') end
    local frenzy=allowed and branch=='xueyan' and math.floor(s.frenzy/2) or 0
    scopedBoosts(id,'frenzy_stats_',frenzy,0)
    if E.sword(id,true) then E.status(id,'ESC_OFFHAND_SWORD',-1,id) else E.removeStatus(id,'ESC_OFFHAND_SWORD',id) end
    -- Native rank markers retain their original lifetime across equipment changes.
end
local function setFrenzy(id,value)
    local s=state(id);if not s then return end
    s.frenzy=R.clamp(value,0,15);save(id,s)
    if s.frenzy>0 then E.status(id,'ESC_FRENZY',-1,id) else E.removeStatus(id,'ESC_FRENZY',id) end
    for i=1,15 do
        local name='ESC_FRENZY_AT_LEAST_'..i
        if i<=s.frenzy and not E.hasStatus(id,name) then E.status(id,name,-1,id)
        elseif i>s.frenzy and E.hasStatus(id,name) then E.removeStatus(id,name,id) end
    end
    refresh(id)
end
local function addFrenzy(id,amount) local s=state(id);if s then setFrenzy(id,s.frenzy+amount) end end
local function helper(id,key,target,meta)
    local spell=helpers[key]
    local copied={};for name,value in pairs(meta or {}) do copied[name]=value end;meta=copied
    if not meta.hand or meta.hand=='auto' then local _,hand=E.preferredSword(id);meta.hand=hand end
    local off=meta.hand=='off'
    if spell and off and Ext.Stats.Get(spell..'_Off',nil,false) then spell=spell..'_Off' end
    if not spell or not Ext.Stats.Get(spell,nil,false) then E.log('Missing native helper '..tostring(key));return false end
    pendingHelpers[id]=pendingHelpers[id] or {}
    local pending={key=key,spell=spell,target=target,meta=meta}
    pendingHelpers[id][#pendingHelpers[id]+1]=pending
    if meta.lineRoot then
        local previous=Line.dispatch;Line.dispatch={id=id,spell=spell,pending=pending}
        local ok,message=pcall(E.useSpell,id,spell,target)
        Line.dispatch=previous
        if not ok then
            E.log('One-line native dispatch failed: '..tostring(message))
            Line.cancel(casts[meta.lineRoot]);return false
        end
        return true
    end
    if not meta.tiandiToken then E.useSpell(id,spell,target);return true end
    -- A target-less failure can be raised inside UseSpell. Keep that exact
    -- request, including across nested helper calls; never guess queue order.
    local previous=tiandiDispatch
    tiandiDispatch={id=id,spell=spell,pending=pending}
    local ok,message=pcall(E.useSpell,id,spell,target)
    tiandiDispatch=previous
    if not ok then
        E.log('Tianqing native dispatch failed: '..tostring(message))
        if not pending.action then
            for i,request in ipairs(pendingHelpers[id] or {}) do
                if request==pending then table.remove(pendingHelpers[id],i);break end
            end
            return false
        end
    end
    return true
end
local function cooperation(c,target)
    if E.friend(c.id,target) then
        c.supportReward=(c.supportReward or 0)+R.cooperation(E.class(c.id));return true
    end
    return false
end
local function settleSupportReward(c)
    local amount=c.supportReward or 0;if amount<=0 then return end
    c.supportReward=nil
    local id,generation=actorId(c.id),pendingSessionLoad
    -- Native CastedSpell precedes UseCosts payment (observed on both H26
    -- domain casts). The next engine Tick has the paid amount. Keep earned
    -- support attached to this action; never infer it from another resource
    -- change or carry native resource userdata across the event boundary.
    Ext.OnNextTick(function()
        if generation~=pendingSessionLoad or c.failed or c.invalid or not E.entity(id) then return end
        E.restore(id,amount)
    end)
end
local function recipients(owner,range,includeSelf)
    return E.nearby(owner,range,function(a,b)
        -- Story callbacks may use Name_GUID while nearby actors use ECS GUIDs.
        -- Self inclusion must not depend on the native party relation to self.
        if E.sameEntity(a,b) then return includeSelf end
        return E.friend(a,b)
    end)
end
local function statusOwner(id,name)
    local entity=E.entity(id)
    -- BG3SE's ECS container maps status entity handles to FixedString IDs.
    -- Legacy status objects instead expose the documented StatusSource field.
    for handle,status in pairs(entity and entity.StatusContainer and entity.StatusContainer.Statuses or {}) do
        if type(status)=='string' then
            if status==name then
                local effect=E.entity(handle)
                if effect and effect.ServerStatusCause then
                    return tostring(effect.ServerStatusCause.Cause),effect.ServerStatusCause.StoryActionId
                end
                return effect and effect.StatusCause and E.uuid(E.entity(effect.StatusCause.Cause)) or nil
            end
        elseif status.StatusId==name then return E.uuid(E.entity(status.StatusSource)),status.StoryActionID end
    end
end
local domainVisuals={
    {status='ESC_VFX_BLOOD_DOMAIN',key='xueyan_xuehai',branch='xueyan'},
    {status='ESC_VFX_SWORD_DOMAIN',key='taixuan_taiqing',branch='taixuan'}}
local partyDomainVisuals={
    {status='ESC_VFX_DAMAGE_SHARE',key='xingge_fengyu',record='xingge_fengyu_status',includeSelf=false},
    {status='ESC_VFX_TEAM_RESONANCE',key='xingge_zhangjian',record='xingge_zhangjian_status',includeSelf=true}}
local function schoolVisualRecord(key)
    local vfx=spec.schoolPolishVfx
    local row=vfx and vfx.enabled and vfx.records and vfx.records[key]
    return row and type(row.effect)=='string' and row.effect~='' and row or nil
end
local function playSchoolVisual(target,key)
    local row=schoolVisualRecord(key)
    if row and E.entity(target) then
        -- Same installed story-header overload used by XueyanEchoVfx: an
        -- actual entity, effect resource, attachment bone and scale.
        pcall(Osi.PlayEffect,target,row.effect,'Dummy_Root',1)
    end
end
local function visualActorAlive(id)
    return E.alive(id) and E.hp(id)>0 and not E.hasStatus(id,'DYING')
end
local function syncPartyDomainVisuals(desired)
    -- A union of beneficiaries makes overlapping owners one visual, without
    -- refreshing the native status on every aura tick or touching aura boosts.
    -- Reconcile one entity once. A watched Name_GUID alias must not remove a
    -- visual that the same entity's desired ECS GUID just requested.
    local candidates,canonicalDesired={},{}
    local function candidate(id)
        local uuid=E.uuid(E.entity(id))
        if uuid then candidates[uuid]=true end
        return uuid
    end
    for id in pairs(watched) do candidate(id) end
    for id in pairs(auraVisualTargets) do candidate(id) end
    for id,statuses in pairs(desired) do
        local uuid=candidate(id)
        if uuid then
            canonicalDesired[uuid]=canonicalDesired[uuid] or {}
            for status,wanted in pairs(statuses) do
                if wanted then canonicalDesired[uuid][status]=true end
            end
        end
    end
    for id in pairs(candidates) do
        if E.entity(id) then
            for _,visual in ipairs(partyDomainVisuals) do
                if canonicalDesired[id] and canonicalDesired[id][visual.status] then
                    if not E.hasStatus(id,visual.status) then E.status(id,visual.status,-1,id) end
                elseif E.hasStatus(id,visual.status) then E.removeStatus(id,visual.status,id) end
            end
        end
    end
    auraVisualTargets=canonicalDesired
end
local function syncDomainVisual(owner,level,branch,visual)
    -- Native Blood Robe also represents siphon shields; native Sword Domain
    -- can remain after death clears domains. Only the persisted, valid domain
    -- authorizes a dedicated visual status, which adds no gameplay boost.
    local enabled=spec.schoolPolishVfx and spec.schoolPolishVfx.enabled
        and Ext.Stats.Get(visual.status,nil,false)~=nil
    local active=enabled and level>0 and branch==visual.branch and E.alive(owner)
        and E.allowed(owner,branch,false) and validDomain(owner,visual.key)
    if active then
        if not E.hasStatus(owner,visual.status) then E.status(owner,visual.status,-1,owner) end
    elseif E.hasStatus(owner,visual.status) then E.removeStatus(owner,visual.status,owner) end
end
local function updateAuras()
    for id in pairs(watched) do
        local entity=E.entity(id);local uuid=E.uuid(entity)
        if not entity then watched[id]=nil;auraTargets[id]=nil;rescueRequests[id]=nil
        elseif uuid and uuid~=id then watched[id]=nil;watched[uuid]=true
        elseif not needsPeriodic(id,entity.Vars.ESC_State) then retireEmptyState(id,entity.Vars.ESC_State) end
    end
    local rows,expiredProtectionStatuses,visualRows={},{},{}
    local actors=watchedActors()
    for owner in pairs(actors) do
        local level,branch=E.class(owner)
        for _,visual in ipairs(domainVisuals) do syncDomainVisual(owner,level,branch,visual) end
        if level>0 and branch=='xingge' and visualActorAlive(owner) and E.allowed(owner,branch,false) then
            for _,visual in ipairs(partyDomainVisuals) do
                if schoolVisualRecord(visual.record) and Ext.Stats.Get(visual.status,nil,false)
                    and validDomain(owner,visual.key) then
                    for _,target in ipairs(recipients(owner,6,visual.includeSelf)) do
                        if visualActorAlive(target) then
                            visualRows[target]=visualRows[target] or {};visualRows[target][visual.status]=true
                        end
                    end
                end
            end
        end
        if level>0 and E.alive(owner) then
            if branch=='xingge' and E.allowed(owner,branch,false) then
                local party=recipients(owner,3,false)
                if #party>0 then
                    party[#party+1]=owner
                    for _,target in ipairs(party) do
                        rows[target]=rows[target] or {};rows[target].side=math.max(rows[target].side or 0,level>=11 and 2 or 1)
                        rows[target].sideReduction=math.max(rows[target].sideReduction or 0,level>=11 and .15 or .10)
                    end
                end
            end
            local swordDomain=validDomain(owner,'taixuan_taiqing')
            local teamDomain=validDomain(owner,'xingge_zhangjian')
            if swordDomain or teamDomain then
                for _,target in ipairs(recipients(owner,6,true)) do
                    rows[target]=rows[target] or {}
                    if swordDomain then rows[target].domain=true end
                    if teamDomain then rows[target].team=true end
                end
            end
            if swordDomain then
                for _,target in ipairs(E.nearby(owner,6,E.enemy)) do rows[target]=rows[target] or {};rows[target].hostileDomain=true end
            end
        end
    end
    for id in pairs(actors) do
        local s=state(id);local dr=0;local changed=false
        local chengfeng,chengfengMovement=false,false
        local protectionOwner,protectionAction=statusOwner(id,'ESC_XINGGE_PROTECTION')
        for key,mark in pairs(s.marks) do
            local owner=key:match('^[^:]+:(.+)$')
            local source=owner and E.entity(owner)
            local ownerState=source and state(owner)
            if not ownerState or ownerState.turn>=(mark.expires or 0) then s.marks[key]=nil;changed=true end
        end
        for key,p in pairs(s.protections) do
            local owner=state(p.owner)
            if not owner or not E.alive(p.owner) or (p.kind=='huifeng' and not E.hasStatus(id,'ESC_XINGGE_PROTECTION'))
                or (p.kind=='huifeng' and protectionOwner and not E.sameEntity(protectionOwner,p.owner))
                or (p.kind=='huifeng' and protectionAction and p.action and protectionAction~=p.action)
                or owner.turn>=p.expires then
                s.protections[key]=nil
                changed=true
                if p.kind=='huifeng' and E.sameEntity(protectionOwner,p.owner) and (not protectionAction or not p.action or protectionAction==p.action)
                    and E.hasStatus(id,'ESC_XINGGE_PROTECTION') then
                    expiredProtectionStatuses[#expiredProtectionStatuses+1]={target=id,owner=p.owner,action=p.action}
                end
            else
                dr=math.max(dr,p.reduction)
                if p.kind=='chengfeng' then
                    chengfeng=true
                    -- Old saved records retain their original single deadline.
                    if owner.turn<(p.movementExpires or p.expires) then chengfengMovement=true end
                end
            end
        end
        -- Resolve all owners before changing the shared recipient slots: expiry
        -- of one cast cannot remove another owner's still-active support.
        if chengfeng or s.boosts.chengfeng or s.boosts.chengfeng_oa or s.boosts.chengfeng_movement then
            syncChengfengBoosts(id,chengfeng,chengfengMovement)
        end
        if dr>0 then rows[id]=rows[id] or {};rows[id].protectionDR=dr end
        for key,debuff in pairs(s.debuffs) do
            local owner=state(debuff.owner)
            if not owner or owner.turn>=debuff.expires then s.debuffs[key]=nil;changed=true
            else
                rows[id]=rows[id] or {};local row=rows[id]
                row.breakAC=math.max(row.breakAC or 0,math.abs(debuff.ac or 0))
                row.attackDown=math.max(row.attackDown or 0,math.abs(debuff.attack or 0))
                row.slow=row.slow or debuff.slow
            end
        end
        if changed then save(id,s) else retireEmptyState(id,s) end
        syncFollowupBoostAliases(id)
    end
    for _,protection in ipairs(expiredProtectionStatuses) do
        local owner,action=statusOwner(protection.target,'ESC_XINGGE_PROTECTION')
        if E.sameEntity(owner,protection.owner) and (not action or not protection.action or action==protection.action) then
            E.removeStatus(protection.target,'ESC_XINGGE_PROTECTION',protection.owner)
        end
    end
    syncPartyDomainVisuals(visualRows)
    for target in pairs(auraTargets) do if not rows[actorId(target)] then E.setBoosts(target,'aura','') end end
    auraTargets=rows
    for target,aura in pairs(rows) do
        local boosts={}
        local ac=(aura.side or 0)-math.max(aura.breakAC or 0,aura.hostileDomain and 2 or 0)
        if ac~=0 then boosts[#boosts+1]='AC('..ac..')' end
        if aura.domain or aura.team then boosts[#boosts+1]='RollBonus(Attack,2)' end
        local attack=math.max(aura.attackDown or 0,aura.hostileDomain and 2 or 0)
        if attack>0 then boosts[#boosts+1]='RollBonus(Attack,-'..attack..')' end
        if aura.hostileDomain or aura.slow then boosts[#boosts+1]='ActionResourceMultiplier(Movement,50,0)' end
        E.setBoosts(target,'aura',table.concat(boosts,';'))
    end
end
-- A retired menu action is replaced by the player's completed single-target
-- sword attack. Never choose from an AoE victim list or an automatic helper.
local function focusEnemy(owner,target)
    local entity=E.entity(target);local uuid=E.uuid(entity)
    if not uuid or Osi.IsCharacter(uuid)~=1 or not E.enemy(owner,uuid)
        or not E.alive(uuid) or E.hp(uuid)<=0 or E.hasStatus(uuid,'DYING') then return nil end
    -- Native status/boost data owns invulnerability; do not infer it from Force
    -- resistance or immortality, which are different gameplay properties.
    for _,entry in pairs(entity.BoostsContainer and entity.BoostsContainer.Boosts or {}) do
        if tostring(entry.Type)=='Invulnerable' then for _ in pairs(entry.Boosts or {}) do return nil end end
    end
    for _,entry in pairs(entity.StatusContainer and entity.StatusContainer.Statuses or {}) do
        local name=controlStatusName(entry)
        local stat=name and Ext.Stats.Get(name,nil,false)
        if stat and type(stat.Boosts)=='string' and stat.Boosts:find('Invulnerable()',1,true) then return nil end
    end
    return uuid
end
local function ensureTaiqingFocus(id)
    local s=state(id);if not s then return end
    -- Keep a living existing focus even outside the domain. It receives no
    -- extra swords there; returning to the radius restores the normal focus.
    if focusEnemy(id,s.focus) then return end
    local target,distance
    for _,enemy in ipairs(E.nearby(id,6,E.enemy)) do
        local candidate=focusEnemy(id,enemy)
        if candidate then
            local d=E.distance(id,candidate)
            if not distance or d<distance-1e-6 or math.abs(d-distance)<=1e-6 and candidate<target then target,distance=candidate,d end
        end
    end
    s.focus=target;save(id,s)
end
local function updateAttackFocus(c)
    if c.branch~='taixuan' or c.level<9 or c.invalid or c.failed or c.focusAmbiguous
        or Osi.IsPlayer(c.id)~=1 or not E.alive(c.id) or not E.allowed(c.id,c.branch,true)
        or c.alias.internal or c.alias.bonusOnly or c.alias.continuation or next(c.meta or {}) then return end
    local row=spec.spells[c.key]
    if not c.basicSword and not (row and row.kind=='attack' and row.action=='sword' and not row.retired) then return end
    local stat=Ext.Stats.Get(c.spell,nil,false)
    local costs=stat and stat.UseCosts
    local paid=type(costs)=='string' and ((';'..costs..';'):find(';ActionPoint:1;',1,true)
        or (';'..costs..';'):find(';ESC_SwordOpportunity:1;',1,true))
    if not paid
        or stat.ContainerSpells and stat.ContainerSpells~='' then return end
    local target=focusEnemy(c.id,c.primaryTarget)
    if target then local s=state(c.id);s.focus=target;save(c.id,s) end
end
local function startDomain(id,key)
    local s=state(id);s.domains[key]=R.applyDuration(s.domains[key],s.turn,4)
    sequence=sequence+1;s.domains[key].sequence=sequence;save(id,s)
    E.status(id,domainStatuses[key],4,id);updateAuras()
end
local function pulse(id,key)
    if not validDomain(id,key) then return end
    local s=state(id);local focus=key=='taixuan_taiqing' and focusEnemy(id,s.focus)
    for _,target in ipairs(E.nearby(id,6,E.enemy)) do
        helper(id,key=='taixuan_taiqing' and 'internal_taiqing_pulse' or 'internal_blood_pulse',target,
            key=='taixuan_taiqing' and {rainIndex=1,rainFocused=E.sameEntity(focus,target)} or nil)
        if key=='taixuan_taiqing' and E.sameEntity(focus,target) then helper(id,'internal_taiqing_pulse',target,{rainIndex=2,rainFocused=true});helper(id,'internal_taiqing_pulse',target,{rainIndex=3,rainFocused=true}) end
    end
end
-- Leave the native TurnStarted event before dispatching an immediate spell.
-- One bounded game-timer callback; no blind retry or compensating damage.
local function scheduleDomainTurnPulse(id,key)
    local entity=E.entity(id);local s=entity and state(id)
    local domain=s and validDomain(id,key)
    if not domain then return end
    local owner=E.uuid(entity) or id
    local expectedBranch=key=='taixuan_taiqing' and 'taixuan' or 'xueyan'
    local pending={turn=s.turn,sequence=domain.sequence,generation=timerGeneration}
    pendingDomainTurnPulses[owner]=pendingDomainTurnPulses[owner] or {}
    pendingDomainTurnPulses[owner][key]=pending
    Ext.Timer.WaitFor(1,function()
        local queued=pendingDomainTurnPulses[owner]
        if not queued or queued[key]~=pending then return end
        queued[key]=nil
        if pending.generation~=timerGeneration then return end
        local currentEntity=E.entity(id);if not currentEntity then return end
        local current=state(id);local active=validDomain(id,key)
        local level,branch=E.class(id)
        if current.turn~=pending.turn or not active or active.sequence~=pending.sequence
            or level<=0 or branch~=expectedBranch or not E.alive(id) or not E.combat(id)
            or not currentEntity.TurnBased or not currentEntity.TurnBased.IsActiveCombatTurn
            or not E.allowed(id,branch,false) then return end
        pulse(id,key)
    end)
end
local function copyPosition(point) return point and {point[1],point[2],point[3]} or nil end
local function finitePosition(point)
    if not point then return false end
    for i=1,3 do local n=point[i];if type(n)~='number' or n~=n or math.abs(n)==math.huge then return false end end
    return true
end
local function playYixiantianBeam(c,phase)
    local config=spec.yixiantianVfx
    if c.key~='taixuan_yixiantian' or not config or not config.enabled
        or c.yixiantianBeamAttempted or c.yixiantianBeamCancelled or c.failed or c.invalid or c.level==0 then return false end
    if type(config.effect)~='string' or config.effect==''
        or not finitePosition(c.startPosition) or not finitePosition(c.position) then return false end
    local okOwner,alive=pcall(function() return E.entity(c.id) and E.alive(c.id) end)
    if not okOwner or not alive then return false end
    local p,q=c.startPosition,c.position
    local dx,dz=q[1]-p[1],q[3]-p[3];local length=math.sqrt(dx*dx+dz*dz)
    if length<1e-6 or length~=length or length==math.huge then return false end
    -- Actual selected point and cast-start snapshot. Match existing planar R.inLine.
    -- Continuous form of vanilla GLO_Spells_PostEA.txt: (270-angleX)%360.
    -- -Z mesh forward; native PlayEffect rotation still requires cardinal calibration.
    local yaw=(-math.deg(math.atan(dx,-dz)))%360
    local height=config.heightOffset or .8
    if type(height)~='number' or height~=height or math.abs(height)==math.huge then return false end
    c.yixiantianBeamAttempted=true
    local ok,message=pcall(Osi.PlayEffectAtPositionAndRotation,config.effect,p[1],p[2]+height,p[3],yaw,1)
    if not ok then E.log('Yixiantian beam visual call failed: '..tostring(message));return false end
    c.yixiantianBeamPlayed=true
    trace('YixiantianBeam',{source=c.id,action=c.action,spell=c.spell,phase=phase,effect=config.effect,
        start=c.startPosition,selected=c.position,finish={p[1]+dx/length*30,p[2],p[3]+dz/length*30},yaw=yaw})
    return true
end
local function playNifengLine(c,phase)
    local config=spec.nifengLineVfx
    if not c or c.key~='tianqing_nifeng' or not config or not config.enabled
        or not c.alias or c.alias.internal or not c.alias.hand or c.level==0 or c.invalid
        or c.nifengLineAttempted or c.nifengLineCancelled then return false end
    if type(c.action)~='number' or c.action<=0 or c.action%1~=0 then return false end
    -- A real MissedBy may follow CastSpellFailed. Only that native evidence
    -- permits this visual; never clear c.failed or execute gameplay completion.
    if c.failed and phase~='MissedBy' then return false end
    if type(config.effect)~='string' or config.effect==''
        or not finitePosition(c.startPosition) or not finitePosition(c.areaCenter) then return false end
    local okOwner,alive=pcall(function() return E.entity(c.id) and E.alive(c.id) end)
    if not okOwner or not alive then return false end
    -- areaCenter is the first explicit UsingSpellAtPosition snapshot. Target
    -- callbacks and later actor movement cannot turn this whole-cast sword line.
    local p,q=c.startPosition,c.areaCenter
    local dx,dz=q[1]-p[1],q[3]-p[3];local length=math.sqrt(dx*dx+dz*dz)
    if length<1e-6 or length~=length or length==math.huge then return false end
    local yaw=(-math.deg(math.atan(dx,-dz)))%360
    local height=config.heightOffset or .8
    if type(height)~='number' or height~=height or math.abs(height)==math.huge then return false end
    c.nifengLineAttempted=true
    local ok,message=pcall(Osi.PlayEffectAtPositionAndRotation,config.effect,p[1],p[2]+height,p[3],yaw,1)
    if not ok then E.log('Nifeng line visual call failed: '..tostring(message));return false end
    trace('NifengLine',{source=c.id,action=c.action,spell=c.spell,trigger=phase,effect=config.effect,
        start=c.startPosition,selected=q,finish={p[1]+dx/length*12,p[2],p[3]+dz/length*12},yaw=yaw})
    return true
end
local function cancelWorldSwordLineOwner(id)
    for _,c in pairs(casts) do
        if E.sameEntity(c.id,id) then
            if c.key=='taixuan_yixiantian' then c.yixiantianBeamCancelled=true;Line.cancel(c)
            elseif c.key=='tianqing_nifeng' then c.nifengLineCancelled=true end
        end
    end
end
local function tianqingRecord(key)
    local config=spec.tianqingVfx
    return config and config.enabled and config.records and config.records[key] or nil
end
local function playGroundEffect(effect,point)
    if type(effect)~='string' or effect=='' or not finitePosition(point) then return false end
    -- BG3 story_header.div: EFFECTRESOURCE, X, Y, Z, Scale (five inputs).
    Osi.PlayEffectAtPosition(effect,point[1],point[2],point[3],1)
    return true
end
local function playTianqing(c,point)
    local row=tianqingRecord(c.key)
    if not row or c.tianqingPlayed or c.failed or not E.entity(c.id) or not E.alive(c.id) then return false end
    if c.key=='tianqing_bafang' then
        local layout=spec.tianqingVfx.bafang
        if not layout or not finitePosition(point) then return false end
        c.tianqingPlayed=true
        for i=0,(layout.count or 8)-1 do
            local angle=math.rad((layout.angleOffset or 22.5)+i*360/(layout.count or 8))
            local p={point[1]+(layout.radius or 8)*math.cos(angle),point[2],point[3]+(layout.radius or 8)*math.sin(angle)}
            local radius=layout.terrainSearchRadius or 1
            -- Official FindValidPosition searches the AI grid, not a raycast.
            local ok,x,y,z=pcall(Osi.FindValidPosition,p[1],p[2],p[3],radius,'NULL_00000000-0000-0000-0000-000000000000',0)
            local found={x,y,z}
            if ok and finitePosition(found) and (x-p[1])^2+(z-p[3])^2<=radius^2 and math.abs(y-p[2])<=6 then p=found
            else E.log('Tianqing eight-direction ground query failed or exceeded bounds; using the selected center plane.') end
            playGroundEffect(layout.effect,p)
        end
        return true
    end
    if not finitePosition(point) then return false end
    c.tianqingPlayed=true
    return playGroundEffect(row.effect,point)
end
local function rememberTiandi(s,token)
    s.tianqingDone=s.tianqingDone or {}
    for _,done in ipairs(s.tianqingDone) do if done==token then return end end
    s.tianqingDone[#s.tianqingDone+1]=token
    if #s.tianqingDone>8 then table.remove(s.tianqingDone,1) end
end
local function cancelTiandi(id,token)
    local entity=E.entity(id);local s=entity and entity.Vars.ESC_State
    if s and s.tianqingStages then
        if token then rememberTiandi(s,token);s.tianqingStages[token]=nil
        else for active in pairs(s.tianqingStages) do rememberTiandi(s,active) end;s.tianqingStages={} end
        save(id,s)
    end
    for handle,entry in pairs(tianqingTimerHandles) do
        if E.sameEntity(entry.id,id) and (not token or entry.token==token) then
            if Ext.Timer.Cancel then Ext.Timer.Cancel(handle) end
            tianqingTimerHandles[handle]=nil
        end
    end
    for owner,queue in pairs(pendingHelpers) do
        if E.sameEntity(owner,id) then
            for i=#queue,1,-1 do if queue[i].meta.tiandiToken and (not token or queue[i].meta.tiandiToken==token) then table.remove(queue,i) end end
        end
    end
end
local tiandiTimer
local function scheduleTiandi(ms,args)
    -- Norbyte Timer.inl serializes this args table and freezes remaining game
    -- time across saves. The third input is a payload, not a Lua callback.
    local s=state(args.id);local entry=s and s.tianqingStages and s.tianqingStages[args.token]
    if not entry then return end
    entry.pending={kind=args.kind,stage=args.stage,delayMs=ms};save(args.id,s)
    local handle
    if Ext.Timer.WaitForPersistent and Ext.Timer.RegisterPersistentHandler then
        handle=Ext.Timer.WaitForPersistent(ms,'ESC_TianqingStage',args)
    else
        local generation=timerGeneration
        handle=Ext.Timer.WaitFor(ms,function() if generation==timerGeneration then tiandiTimer(args) end end)
    end
    if handle then tianqingTimerHandles[handle]={id=args.id,token=args.token} end
end
local function tiandiParent(id,entry,token)
    local c=casts[entry.action]
    if not c or c.id~=id or c.key~='tianqing_tiandi' then
        c={id=id,key='tianqing_tiandi',spell=entry.spell,action=entry.action,alias={hand=entry.hand},meta={},
            targets={},rewards={},firstHits={},finished=true,branch='tianqing',level=E.class(id)}
        casts[entry.action]=c
    end
    c.tianqingToken=token;c.controlApplied=entry.controlApplied or {};entry.controlApplied=c.controlApplied
    return c
end
local function tiandiEntry(id,token)
    local entity=E.entity(id);local s=entity and entity.Vars.ESC_State
    return s and s.tianqingStages and s.tianqingStages[token],s
end
local function tiandiLedger(entry,target)
    local ledgers=entry and entry.targetLedger
    if not ledgers or not target then return end
    if ledgers[target] then return ledgers[target] end
    -- Damage callbacks use UUIDs; Osiris and older saved queues can use Name_GUID.
    for id,ledger in pairs(ledgers) do if E.sameEntity(id,target) then return ledger end end
end
local function isTiandiHelper(key)
    return key=='internal_tiandi_stage' or key=='internal_tiandi_stage_nocontrol'
end
local function finishTiandiIfIdle(id,entry,token)
    if entry.resolved~=3 then return end
    for _,ledger in pairs(entry.targetLedger or {}) do if ledger.inFlight or #ledger.queue>0 then return end end
    cancelTiandi(id,token)
end
local dispatchTiandiTarget
local function completeTiandiHelper(c)
    local token=c.meta.tiandiToken;local entry,s=tiandiEntry(c.id,token)
    local ledger=tiandiLedger(entry,c.target)
    local flight=ledger and ledger.inFlight
    if not flight or flight.stage~=c.meta.tiandiStage or flight.action and flight.action~=c.action then return end
    ledger.inFlight=nil;save(c.id,s)
    dispatchTiandiTarget(c.id,entry,token,c.target)
    finishTiandiIfIdle(c.id,entry,token)
end
local function finishTiandiHelper(c,failed)
    if not c.meta.tiandiToken then return end
    local entry,s=tiandiEntry(c.id,c.meta.tiandiToken)
    local ledger=tiandiLedger(entry,c.target)
    local flight=ledger and ledger.inFlight
    if not flight or flight.stage~=c.meta.tiandiStage or flight.finished then return end
    flight.finished=true;flight.failed=failed or false;save(c.id,s)
    -- These helpers are Target casts, with no travelling projectile. Allow
    -- adjacent native HitMarker/CastedSpell callbacks to finish their batch.
    if failed then completeTiandiHelper(c)
    else local generation=timerGeneration;Ext.Timer.WaitFor(1,function() if generation==timerGeneration then completeTiandiHelper(c) end end) end
end
dispatchTiandiTarget=function(id,entry,token,target)
    local ledger=tiandiLedger(entry,target)
    if not ledger or ledger.inFlight or #ledger.queue==0 then return end
    if not E.entity(target) or not E.alive(target) then ledger.queue={};save(id,state(id));return end
    local stage=table.remove(ledger.queue,1)
    local key=ledger.controlAttempted and 'internal_tiandi_stage_nocontrol' or 'internal_tiandi_stage'
    local meta={parentAction=entry.action,hand=entry.hand,tiandiStage=stage,tiandiToken=token,target=target}
    ledger.inFlight={stage=stage,key=key,meta=meta};save(id,state(id))
    if not helper(id,key,target,meta) then ledger.inFlight=nil;save(id,state(id));dispatchTiandiTarget(id,entry,token,target) end
end
tiandiTimer=function(args,handle)
    if handle then tianqingTimerHandles[handle]=nil end
    local s=state(args.id);local entry=s and s.tianqingStages and s.tianqingStages[args.token]
    if not entry then return end
    local level,branch=E.class(args.id)
    if not E.entity(args.id) or not E.alive(args.id) or level==0 or branch~='tianqing' then cancelTiandi(args.id,args.token);return end
    local config=spec.tianqingVfx and spec.tianqingVfx.tiandi
    if not config or not spec.tianqingVfx.enabled then cancelTiandi(args.id,args.token);return end
    local phase=args.stage;local c=tiandiParent(args.id,entry,args.token)
    if c.failed then cancelTiandi(args.id,args.token);return end
    if args.kind=='play' and entry.played==phase-1 and entry.resolved==phase-1 then
        entry.pending=nil;entry.played=phase;save(args.id,s)
        if spec.tianqingVfx.enabled then playGroundEffect(config.effect,entry.center) end
        scheduleTiandi(config.hitTimeMs or 800,{id=args.id,token=args.token,stage=phase,kind='resolve'})
    elseif args.kind=='resolve' and entry.played==phase and entry.resolved==phase-1 then
        -- Commit before issuing native casts. Repeated/restored callbacks can
        -- never dispatch this stage twice, including a save between stages.
        entry.pending=nil;entry.resolved=phase;save(args.id,s)
        entry.targetLedger=entry.targetLedger or {}
        for _,target in ipairs(entry.targets) do
            entry.targetLedger[target]=entry.targetLedger[target] or {queue={},controlAttempted=false}
            local ledger=entry.targetLedger[target];ledger.queue[#ledger.queue+1]=phase;save(args.id,s)
            dispatchTiandiTarget(args.id,entry,args.token,target)
        end
        if phase<3 then
            scheduleTiandi(math.max(1,(config.intervalMs or 1000)-(config.hitTimeMs or 800)),
                {id=args.id,token=args.token,stage=phase+1,kind='play'})
        else finishTiandiIfIdle(args.id,entry,args.token) end
    end
end
if Ext.Timer.RegisterPersistentHandler then Ext.Timer.RegisterPersistentHandler('ESC_TianqingStage',tiandiTimer) end
local function startTiandi(c)
    local config=spec.tianqingVfx and spec.tianqingVfx.tiandi
    if not config or not spec.tianqingVfx.enabled or c.tianqingToken or not c.alias.hand or c.alias.internal then return end
    local center=c.areaCenter or c.position or c.targetPosition
    if not finitePosition(center) then E.log('Tianqing stage cast has no fixed area center.');return end
    local token=tostring(c.action);local s=state(c.id);if not s then return end
    for _,done in ipairs(s.tianqingDone or {}) do if done==token then return end end
    if s.tianqingStages and s.tianqingStages[token] then c.tianqingToken=token;return end
    local targets,seen={},{}
    for target in pairs(c.tiandiTargets or {}) do
        local id=E.uuid(E.entity(target)) or target
        if not seen[id] then targets[#targets+1]=id;seen[id]=true end
    end
    table.sort(targets)
    s.tianqingStages=s.tianqingStages or {}
    s.tianqingStages[token]={action=c.action,spell=c.spell,hand=c.alias.hand,center=copyPosition(center),targets=targets,
        played=0,resolved=0,controlApplied=c.controlApplied or {},targetLedger={}}
    c.tianqingToken=token;save(c.id,s)
    tiandiTimer({id=c.id,token=token,stage=1,kind='play'})
end
local function bindPendingHelper(c,target)
    if c.helperMetaBound then return end
    local dispatch=c.key=='internal_yixiantian_hit' and Line.dispatch or tiandiDispatch
    if dispatch and E.sameEntity(dispatch.id,c.id) and dispatch.spell==c.spell
        and (not dispatch.pending.action or dispatch.pending.action==c.action)
        and (not target or E.sameEntity(target,dispatch.pending.target)) then
        for i,pending in ipairs(pendingHelpers[dispatch.id] or {}) do
            if pending==dispatch.pending then
                table.remove(pendingHelpers[dispatch.id],i)
                pending.action=c.action;c.meta=pending.meta;c.helperMetaBound=true;c.target=pending.target
                return
            end
        end
    end
    -- A target-less event outside our native call cannot identify one of
    -- several outstanding stages. Wait for a real target or explicit failure.
    if (isTiandiHelper(c.key) or c.key=='internal_yixiantian_hit') and not target then return end
    if c.key=='internal_yixiantian_hit' then
        local found,foundQueue,foundIndex
        for owner,queue in pairs(pendingHelpers) do
            if E.sameEntity(owner,c.id) then
                for i,pending in ipairs(queue) do
                    if pending.key==c.key and E.sameEntity(target,pending.target) then
                        if found then return end -- ambiguous overlapping roots: do not guess
                        found,foundQueue,foundIndex=pending,queue,i
                    end
                end
            end
        end
        if found then
            table.remove(foundQueue,foundIndex);found.action=c.action;c.meta=found.meta;c.helperMetaBound=true
        end
        return
    end
    local function take(queue)
        for i,pending in ipairs(queue or {}) do
            if pending.key==c.key and (not target or not pending.target or E.sameEntity(target,pending.target)) then
                pending.action=c.action;c.meta=table.remove(queue,i).meta;c.helperMetaBound=true;return true
            end
        end
        return false
    end
    if take(pendingHelpers[c.id]) then return end
    -- Native helper completion can precede UsingSpell/UsingSpellOnTarget, and
    -- Osiris may name the same queued owner as Name_GUID rather than UUID.
    for owner,queue in pairs(pendingHelpers) do
        if owner~=c.id and E.sameEntity(owner,c.id) and take(queue) then return end
    end
end
local function bindTiandiFlight(c)
    if not c.meta.tiandiToken then return end
    local entry,s=tiandiEntry(c.id,c.meta.tiandiToken)
    local ledger=tiandiLedger(entry,c.meta.target or c.target)
    local flight=ledger and ledger.inFlight
    if flight and flight.stage==c.meta.tiandiStage and (not flight.action or flight.action==c.action) then
        flight.action=c.action;flight.spell=c.spell;save(c.id,s)
    end
end
function Line.cancel(root)
    if not root or root.key~='taixuan_yixiantian' then return end
    root.lineCancelled=true;root.lineFlight=nil
    for owner,queue in pairs(pendingHelpers) do
        if E.sameEntity(owner,root.id) then
            for i=#queue,1,-1 do if queue[i].meta.lineRoot==root.action then table.remove(queue,i) end end
        end
    end
end
function Line.parent(c,bind)
    local root=c and c.meta and c.meta.lineRoot and casts[c.meta.lineRoot]
    local flight=root and root.lineFlight
    if not root or root.key~='taixuan_yixiantian' or root.lineCancelled or root.failed
        or root.yixiantianBeamCancelled or root.lineGeneration~=timerGeneration
        or not E.sameEntity(root.id,c.id) or not c.helperMetaBound or not flight
        or not E.sameEntity(flight.target,c.target) or not E.sameEntity(flight.target,c.meta.lineTarget)
        or flight.action and flight.action~=c.action then return nil end
    if bind then flight.action=c.action;c.damageOptions=root.damageOptions;c.alias.hand=root.alias.hand end
    return root
end
function Line.advance(root)
    if casts[root.action]~=root or root.lineCancelled or root.failed or root.yixiantianBeamCancelled
        or root.lineGeneration~=timerGeneration or root.lineFlight or not E.alive(root.id)
        or not E.allowed(root.id,root.branch,true) then return end
    local target=root.lineTargets[root.lineIndex]
    while target and (not E.alive(target) or not E.enemy(root.id,target) or Osi.IsOnStage(target)~=1) do
        root.lineIndex=root.lineIndex+1;target=root.lineTargets[root.lineIndex]
    end
    if not target then root.lineDone=true;Line.settle(root);return end
    root.lineIndex=root.lineIndex+1;root.lineFlight={target=target}
    helper(root.id,'internal_yixiantian_hit',target,{lineRoot=root.action,lineTarget=target,hand=root.alias.hand})
end
function Line.complete(c,failed)
    local root=Line.parent(c,true)
    if not root then return end
    if failed then Line.settle(root);Line.cancel(root);return end
    -- Casted may precede native damage. The final native HitMarker supplies
    -- completion of the whole Target functor list, not a guessed time delay.
    if not c.finished or not c.lineHitSeen or c.lineCompleted then return end
    c.lineCompleted=true;root.lineFlight=nil
    Ext.OnNextTick(function() Line.advance(root) end)
end
function Line.start(c)
    if c.key~='taixuan_yixiantian' or not c.finished or c.lineStarted or c.failed or c.invalid
        or c.yixiantianBeamCancelled or c.level==0 or not finitePosition(c.startPosition)
        or not finitePosition(c.position) or not E.alive(c.id) then return end
    local p,q=c.startPosition,c.position
    local dx,dz=q[1]-p[1],q[3]-p[3];local length=math.sqrt(dx*dx+dz*dz)
    if length<1e-6 then return end
    c.lineStarted=true;c.lineGeneration=timerGeneration;c.lineIndex=1;c.lineHits={};c.lineTargets={};c.lineOrder={}
    local finish={p[1]+dx/length*30,q[2],p[3]+dz/length*30};local targets={}
    for _,target in ipairs(E.nearby(c.id,30,E.enemy)) do
        local inside,t=R.inLine(E.position(target),p,finish,2)
        if inside then targets[#targets+1]={id=target,t=t} end
    end
    table.sort(targets,function(a,b) return a.t<b.t or a.t==b.t and a.id<b.id end)
    local rank=0
    for _,target in ipairs(targets) do
        c.lineTargets[#c.lineTargets+1]=target.id
        if not E.forceImmune(target.id) then c.lineOrder[target.id]=rank;rank=rank+1 end
    end
    playYixiantianBeam(c,'NativeTargetDispatch')
    Line.advance(c)
end
local function failureKey(id,action) return actorId(id)..':'..tostring(action) end
local function rememberRetiredFailure(c)
    local key=failureKey(c.id,c.action)
    if retiredFailures[key] then return end
    retiredFailures[key]=true;retiredFailureOrder[#retiredFailureOrder+1]=key
    -- Retain only lightweight recent rejection receipts, never cast/VFX/target
    -- graphs. The 30s context window still permits late native helper binding.
    if #retiredFailureOrder>512 then retiredFailures[table.remove(retiredFailureOrder,1)]=nil end
end
local function scheduleCastRetirement(c)
    if c.retirementScheduled then return end
    c.retirementScheduled=true
    Ext.Timer.WaitFor(30000,function()
        if casts[c.action]~=c then return end
        if c.failed then rememberRetiredFailure(c) end
        Line.cancel(c);casts[c.action]=nil
        local owner=actorId(c.id)
        for target in pairs(c.targets or {}) do stages[owner..':'..tostring(c.action)..':'..actorId(target)]=nil end
    end)
end
local function beginCast(id,spell,action,target,position)
    local name=E.spellName(spell);local key=keyFor(name);local c=casts[action]
    if retiredFailures[failureKey(id,action)] then
        return {id=id,key=key,spell=name,action=action,alias={internal=true},meta={},targets={},
            rewards={},firstHits={},failed=true,tiandiAbandoned=true,taixuanRainCancelled=true}
    end
    if c and E.sameEntity(c.id,id) then
        if c.tiandiAbandoned then return c end
        c.target=target or c.target;c.position=position and copyPosition(position) or c.position
        if target and not c.targetPosition then c.targetPosition=copyPosition(E.position(target)) end
        if position and not c.areaCenter then c.areaCenter=copyPosition(position) end
        if target and c.primaryTarget and not E.sameEntity(target,c.primaryTarget) then c.focusAmbiguous=true end
        c.primaryTarget=c.primaryTarget or target
        -- Immediate native helpers can deliver CastedSpell first.
        -- Bind their metadata when their actual target arrives; never guess a
        -- target from queue order during the target-less completion callback.
        if target and (c.key=='internal_taiqing_pulse' or c.key=='internal_resonance' or c.key=='internal_yixiantian_hit' or isTiandiHelper(c.key)) then
            bindPendingHelper(c,target);bindTiandiFlight(c)
            if c.key=='internal_yixiantian_hit' then Line.parent(c,true);Line.complete(c,c.failed) end
            if c.finished or c.failed then finishTiandiHelper(c,c.failed) end
        end
        if position then Line.start(c) end
        return c
    end
    if E.class(id)>0 then refresh(id);scopedBoosts(id,'cast_snapshot_',0,0);E.setBoosts(id,'cast_weapon_accuracy','') end
    local alias={};for field,value in pairs(aliases[name] or {}) do alias[field]=value end
    c={id=id,key=key,spell=name,target=target,position=copyPosition(position),action=action,targets={},rewards={},firstHits={},
        alias=alias,startPosition=copyPosition(E.position(id)),targetPosition=target and copyPosition(E.position(target)),
        areaCenter=copyPosition(position),primaryTarget=target}
    bindPendingHelper(c,target)
    c.meta=c.meta or {};c.level,c.branch=E.class(id)
    local foundation=spec.spells[c.alias.parent or key]
    if (c.alias.hand=='auto' or foundation and foundation.base=='AUTO') and not (c.alias.bonusOnly and c.alias.offhand) then
        local _,hand=E.preferredSword(id);c.alias.hand=c.meta.hand or hand
    end
    bindTiandiFlight(c)
    local original=c.meta.originalSpell or name
    c.basicSword=(original=='Target_MainHandAttack' and E.sword(id)~=nil)
        or ((original=='Target_OffhandAttack' or original=='Target_OffHandAttack') and E.sword(id,true)~=nil)
    local sourceState=c.level>0 and state(id) or nil;local aura=auraTargets[E.uuid(E.entity(id)) or id] or {}
    c.damageOptions={domain=aura.domain,team=aura.team,charge=sourceState and sourceState.chargeUntil and sourceState.chargeUntil>sourceState.turn,
        descent=c.level>0 and validDomain(id,'tianqing_tianjian')~=nil}
    if c.key=='internal_yixiantian_hit' then Line.parent(c,true) end
    local row=spec.spells[c.alias.parent or key]
    if row and sourceState and (row.base=='W' or row.base=='WQ') then
        local modifier=E.swordAttribute(id,c.alias.hand=='off' or c.alias.offhand)
        local adjustment=modifier-E.ability(id,'Wisdom')
        E.setBoosts(id,'cast_weapon_accuracy',adjustment>0 and "IF(SpellId('"..name.."')):RollBonus(Attack,"..adjustment..')' or '')
    end
    if c.branch=='xueyan' and key then
        local s=state(id)
        if c.alias.noYuan then
            if s.frenzy<(c.alias.spent or 0) then c.invalid=true else setFrenzy(id,s.frenzy-(c.alias.spent or 0)) end
        else
        local chain=c.alias.continuation and s.chains[c.alias.chain or (key=='xueyan_wusheng' and 'wusheng' or 'liancheng')]
        c.snapshot=chain and chain.snapshot or R.spendFrenzy(s.frenzy,c.alias.spent or 0)
        if c.snapshot.spent>0 then
            if not c.alias.continuation then setFrenzy(id,c.snapshot.remaining) end
            scopedBoosts(id,'cast_snapshot_',c.snapshot.attack-math.floor(state(id).frenzy/2),0)
        end
        end
    end
    casts[action]=c;return c
end
local function retireUnboundTiandiFailure(c)
    if c.meta.tiandiToken or c.tiandiFailurePending then return end
    local candidates={}
    for owner,queue in pairs(pendingHelpers) do
        if E.sameEntity(owner,c.id) then
            for _,pending in ipairs(queue) do
                if pending.key==c.key and pending.spell==c.spell and pending.meta.tiandiToken then
                    local token=pending.meta.tiandiToken
                    local entry=tiandiEntry(owner,token);local ledger=tiandiLedger(entry,pending.target)
                    local flight=ledger and ledger.inFlight
                    if flight and not flight.action then
                        candidates[#candidates+1]={id=owner,token=token,target=pending.target,stage=flight.stage}
                    end
                end
            end
        end
    end
    c.tiandiFailurePending=true
    local generation=timerGeneration
    -- Only an explicit failure reaches here. Allow its adjacent target event
    -- to bind first; this is not a timeout on an otherwise valid native cast.
    Ext.OnNextTick(function()
        if generation~=timerGeneration or c.meta.tiandiToken then return end
        c.tiandiAbandoned=true;c.helperMetaBound=true
        for _,candidate in ipairs(candidates) do
            local entry=tiandiEntry(candidate.id,candidate.token)
            local ledger=tiandiLedger(entry,candidate.target);local flight=ledger and ledger.inFlight
            if flight and not flight.action and flight.stage==candidate.stage then
                E.log('Cancelled unbound Tianqing cast after native failure: '..candidate.token)
                cancelTiandi(candidate.id,candidate.token)
            end
        end
    end)
end
local function failedCast(id,spell,action)
    for key,receipt in pairs(nativeHeals) do if receipt.action==action then nativeHeals[key]=nil end end
    local c=casts[action]
    if keyFor(E.spellName(spell))=='internal_yixiantian_hit' and not (c and c.meta.lineRoot) then
        local dispatch=Line.dispatch
        if dispatch and E.sameEntity(dispatch.id,id) and dispatch.spell==E.spellName(spell)
            and (not dispatch.pending.action or dispatch.pending.action==action) then
            c=beginCast(id,spell,action,dispatch.pending.target)
        else
            -- An unbound asynchronous failure cannot safely identify a target.
            for _,root in pairs(casts) do
                if E.sameEntity(root.id,id) and root.lineFlight then
                    -- Earlier native targets already hit; preserve their one
                    -- reward/echo pass without advancing the failed queue.
                    Line.settle(root);Line.cancel(root)
                end
            end
        end
    end
    if isTiandiHelper(keyFor(E.spellName(spell))) and not (c and c.meta.tiandiToken) then
        local dispatch=tiandiDispatch
        local exact=dispatch and E.sameEntity(dispatch.id,id) and dispatch.spell==E.spellName(spell)
            and (not dispatch.pending.action or dispatch.pending.action==action)
        c=beginCast(id,spell,action,exact and dispatch.pending.target or id)
    end
    if c then
        c.failed=true;Rain.Cancel(c);CastVfx.Cancel(c);c.yixiantianBeamCancelled=true
        scheduleCastRetirement(c)
        if c.key=='internal_yixiantian_hit' then Line.complete(c,true)
        elseif c.key=='taixuan_yixiantian' then Line.cancel(c) end
        finishTiandiHelper(c,true)
        if isTiandiHelper(c.key) then retireUnboundTiandiFailure(c) end
        if c.tianqingToken then cancelTiandi(id,c.tianqingToken)
        elseif c.key=='tianqing_tiandi' and c.alias.hand and not c.alias.internal then
            local s=state(id);if s then rememberTiandi(s,tostring(action));save(id,s) end
        end
    end
    if E.class(id)>0 then scopedBoosts(id,'cast_snapshot_',0,0);E.setBoosts(id,'cast_weapon_accuracy','') end
    trace('CastSpellFailed',{source=id,spell=spell,action=action})
end
local function castEffect(c)
    local id,key,target=c.id,c.key,c.target or c.id;local level,branch=E.class(id)
    if not key or level==0 or c.invalid then return end
    local s=state(id)
    if key=='tiaoxi' or key=='tianqing_xushi' then E.restore(id,R.breath(level,key=='tianqing_xushi' and 'tianqing' or branch,true,E.combat(id)))
    elseif key=='taixuan_guiyuan' or key=='tianqing_nixi' or key=='xueyan_huichao' then
        if target==id then
            E.heal(target,E.maxHp(target)*R.healing(level,branch))
        end
    elseif key=='qi_sword' then
        s.qiSword=false;save(id,s);E.removeStatus(id,'ESC_QI_MODE',id)
    elseif key=='xueyan_damage_mode' then
        s.damageMode=s.damageMode=='Necrotic' and 'Force' or 'Necrotic';save(id,s)
        if s.damageMode=='Force' then E.status(id,'ESC_FORCE_MODE',-1,id) else E.removeStatus(id,'ESC_FORCE_MODE',id) end
    elseif key=='xueyan_ranxue' then
        local hp,frenzy=R.bloodCost(E.hp(id),E.maxHp(id),s.frenzy);if hp then Osi.SetHitpoints(id,hp,'Guaranteed');setFrenzy(id,frenzy) end
    elseif key=='control_release' or key=='xingge_fuchen' then
        if target==id or E.friend(id,target) and E.distance(id,target)<=18 then
            local removed=clearControls(target,id);E.status(target,'ESC_CONTROL_RESISTANCE',2,id);if removed then cooperation(c,target) end
        end
    elseif key=='taixuan_liuguang' then
        if c.target and E.entity(target) and (E.enemy(id,target) or Osi.IsItem(target)==1) then
            for _=1,3 do helper(id,'internal_liuguang_stage',target,{parentAction=c.action,hand=c.alias.hand}) end
        end
    elseif key=='tianqing_tianbeng' then
        local start,finish=c.startPosition,c.targetPosition
        if c.target and start and finish and E.enemy(id,target) then
            local dx,dz=finish[1]-start[1],finish[3]-start[3]
            local direction=math.sqrt(dx*dx+dz*dz)
            if direction>0 then
                for _,enemy in ipairs(E.nearby(id,12,E.enemy)) do
                    local point=E.position(enemy)
                    local x,y,z=point[1]-start[1],point[2]-start[2],point[3]-start[3]
                    local planar=math.sqrt(x*x+z*z)
                    -- Preserve the chosen facing even when the primary hit
                    -- killed or pushed its target before CastedSpell arrives.
                    if not E.sameEntity(enemy,target) and planar>0 and x*x+y*y+z*z<=144+1e-9
                        and (x*dx+z*dz)/(planar*direction)>=math.sqrt(.5)-1e-9 and E.visible(id,enemy) then
                        helper(id,'internal_tianbeng_cone',enemy,{parentAction=c.action,hand=c.alias.hand})
                    end
                end
            end
        end
    elseif key=='xingge_huifeng' then
        if target==id or E.friend(id,target) and E.distance(id,target)<=18 then
            local t=state(target);t.protections['huifeng:'..id]={owner=id,kind='huifeng',action=c.action,expires=s.turn+2,reduction=.20};save(target,t)
            cooperation(c,target);updateAuras()
            for _,enemy in ipairs(E.nearby(target,3,function(_,other) return E.enemy(id,other) end)) do helper(id,'internal_huifeng_control',enemy,{parentAction=c.action}) end
        end
    elseif key=='tianqing_tianfeng' then s.chargeUntil=s.turn+2;save(id,s)
    elseif key=='taixuan_taiqing' or key=='xueyan_xuehai' then
        if key=='taixuan_taiqing' then ensureTaiqingFocus(id) end
        startDomain(id,key);pulse(id,key)
    elseif key=='xingge_fengyu' or key=='xingge_zhangjian' then
        startDomain(id,key)
        if key=='xingge_fengyu' then for _,ally in ipairs(recipients(id,6,false)) do cooperation(c,ally) end end
    elseif key=='xingge_chengfeng' then
        if target==id or E.friend(id,target) then
            local t=state(target);t.protections['chengfeng:'..id]={owner=id,kind='chengfeng',movementExpires=s.turn+1,expires=s.turn+2,reduction=0};save(target,t)
            syncChengfengBoosts(target,true,true);cooperation(c,target)
            for _,enemy in ipairs(E.nearby(target,3,function(_,other) return E.enemy(id,other) end)) do helper(id,'internal_chengfeng_burst',enemy,{parentAction=c.action,hand=c.alias.hand}) end
        end
    elseif key=='xingge_tongzhou' then
        for _,ally in ipairs(recipients(id,6,false)) do
            requestCooperation(ally,id,target,c.action)
        end
    elseif key=='sword_flight' then
        if #E.nearby(id,3,E.enemy)==0 and E.allowed(id,branch,true) then
            E.setResource(id,spec.flightResource,24);E.status(id,'ESC_IN_FLIGHT',1,id)
        end
    elseif key=='internal_flight_move' then
        local pool=E.resourceEntry(id,spec.flightResource)
        if pool and pool.Amount<=0 then E.removeStatus(id,'ESC_IN_FLIGHT',id) end
    elseif key=='internal_chain_move' or key=='xueyan_chuanshen' then
        local p=E.position(id)
        if p and c.startPosition and not R.within(p,c.startPosition,.01) then s.dashUntil=s.turn+2;save(id,s);refresh(id) end
    end
end
local function reductionFactor(target)
    local level,branch=E.class(target);local s=state(target);local factor=1
    if E.allowed(target,branch,false) then
        factor=factor*(1-R.baseReduction(level,branch,s.frenzy))
        if s.guard and E.hasStatus(target,'ESC_COUNTER_READY') then factor=factor*(1-s.guard.reduction) end
        if validDomain(target,'tianqing_tianjian') then factor=factor*.75 end
        if validDomain(target,'xingge_fengyu') then factor=factor*.70 end
    end
    local aura=auraTargets[actorId(target)]
    if aura then factor=factor*(1-(aura.sideReduction or 0))*(1-(aura.protectionDR or 0)) end
    return factor
end
local function transferDamage(target,amount,parts,source)
    if amount<=0 then return end
    local context={target=target,source=source,transfer=true,eligible=false,total=0,emitted=0,factor=reductionFactor(target)}
    local previous=pendingTransfer;pendingTransfer=context
    local ok,err=pcall(function()
        local total=0
        for _,part in ipairs(parts or {}) do total=total+math.max(0,part.Amount) end
        local remaining=amount
        local count=parts and #parts or 0
        if count==0 then E.damageTransfer(target,amount,'Force',source)
        else
            for i,part in ipairs(parts) do
                local value=i==count and remaining or total>0 and math.floor(amount*math.max(0,part.Amount)/total) or 0
                remaining=remaining-value
                if value>0 then E.damageTransfer(target,value,part.DamageType,source) end
            end
        end
    end)
    -- A rejected native call must not classify unrelated later hits as shares.
    -- Preserve the original error; no success receipt or replay after failure.
    pendingTransfer=previous
    if not ok then error(err,0) end
    -- One transfer can contain several native damage types. The visible
    -- receipt belongs to the receiving protector once, after the whole event.
    playSchoolVisual(target,'xingge_fengyu_transfer')
end
local function defense(target,damage,bypass,transfer,parts,stage)
    -- Destructible items keep the native damage/rounding path, but have no
    -- character equipment, class shields or party damage-sharing state.
    local level,branch=E.class(target);local s=E.character(target) and state(target)
    if s and not bypass then
        local other={}
        if E.allowed(target,branch,false) then
            if s.guard and E.hasStatus(target,'ESC_COUNTER_READY') then other[#other+1]=s.guard.reduction end
            if validDomain(target,'tianqing_tianjian') then other[#other+1]=.25 end
            if validDomain(target,'xingge_fengyu') then other[#other+1]=.30 end
            -- Keep floating value until the final stage/target rounding, including aura DR.
            damage=damage*(1-R.baseReduction(level,branch,s.frenzy))
            for _,dr in ipairs(other) do damage=damage*(1-dr) end
        end
        local aura=auraTargets[actorId(target)]
        if aura then damage=damage*(1-(aura.sideReduction or 0))*(1-(aura.protectionDR or 0)) end
    end
    if stage then
        stage.defenseFloat=stage.defenseFloat+math.max(0,damage)
        local cumulative=math.floor(stage.defenseFloat+1e-9)
        damage=cumulative-stage.defenseEmitted;stage.defenseEmitted=cumulative
    else damage=math.floor(math.max(0,damage)+1e-9) end
    if not s then return damage,damage end
    local credited=damage;damage,s.shield=R.shieldAbsorb(damage,s.shield);save(target,s)
    if not transfer then
        local protectors={}
        for owner in pairs(watchedActors()) do
            local domain=validDomain(owner,'xingge_fengyu')
            if domain and not E.sameEntity(owner,target) and E.friend(owner,target) and E.distance(owner,target)<=6 then
                protectors[#protectors+1]={owner=owner,percent=E.class(owner)>=10 and .45 or .40,sequence=domain.sequence or 0}
            end
        end
        local protector=R.chooseShare(protectors)
        if protector and damage>0 then
            -- Native temporary HP absorbs before party transfer; actual engine ordering is
            -- a live-test contract. We leave that portion on the original target's hit.
            local shiftable=math.max(0,damage-E.tempHp(target))
            local shifted=math.floor(shiftable*protector.percent);damage=damage-shifted
            local original=contexts[#contexts]
            transferDamage(protector.owner,shifted,parts,original and original.source or target)
        end
    end
    return damage,credited
end
local function multiplier(context)
    if not E.character(context.source) then return 1 end
    local s=state(context.source);if not s or (not context.eligible and not context.direct) then return 1 end
    local own=context.eligible
    -- Immediate helpers may deal damage before a cast callback creates their context.
    local c=casts[context.action];local alias=c and c.alias or aliases[E.spellName(context.spell)] or {}
    local row=spec.spells[alias.parent or context.key];local snapshot=c and c.snapshot
    local aura=auraTargets[actorId(context.source)] or {};local followup=false
    local options=c and c.damageOptions or {domain=aura.domain,team=aura.team,
        charge=s.chargeUntil and s.chargeUntil>s.turn,descent=validDomain(context.source,'tianqing_tianjian')~=nil}
    for owner in pairs(watchedActors()) do if not E.sameEntity(owner,context.source) and E.friend(owner,context.source)
        and activeMark(context.target,'followup',owner) then followup=true;break end end
    return R.damageMultiplier({level=context.level,held=own and context.branch=='xueyan' and (snapshot and snapshot.held or s.frenzy) or 0,
        spent=own and snapshot and snapshot.spent or 0,weakpoint=own and activeMark(context.target,'weakpoint',context.source)~=nil,
        domain=options.domain,team=options.team,followup=followup,
        charge=own and options.charge,descent=own and options.descent,
        regular=own and row and row.level>=6 and row.level<=9 and row.cost==10})
end
local function stageKey(source,action,target)
    -- Damage hooks use UUIDs, while Osiris cast/hit callbacks can use Name_GUID.
    -- Both identities must settle the same accumulated native damage exactly once.
    local owner=E.uuid(E.entity(source)) or source or '_environment_'
    local victim=E.uuid(E.entity(target)) or target
    return owner..':'..tostring(action)..':'..victim
end
local function ensureStage(context)
    local name=stageKey(context.source,context.action,context.target)
    local stage=stages[name]
    if not stage then
        stage={damage=0,hp=context.hp,level=context.level,branch=context.branch,eligible=context.eligible,
            outgoingFloat=0,outgoingEmitted=0,defenseFloat=0,defenseEmitted=0}
        stages[name]=stage
    end
    return stage
end
local function beforeDamage(evt,context)
    if pendingTransfer and not context then
        local hit=evt.Hit;local total=0
        for _,part in ipairs(hit.DamageList) do total=total+math.max(0,part.Amount) end
        pendingTransfer.total=pendingTransfer.total+total*pendingTransfer.factor
        local cumul=math.floor(pendingTransfer.total+1e-9)
        local delta=cumul-pendingTransfer.emitted;pendingTransfer.emitted=cumul
        local s=state(pendingTransfer.target)
        local final;final,s.shield=R.shieldAbsorb(delta,s.shield);save(pendingTransfer.target,s)
        local remaining=final
        for i,part in ipairs(hit.DamageList) do
            local value=i==#hit.DamageList and remaining or total>0 and math.floor(final*part.Amount/total) or 0
            part.Amount=value;remaining=remaining-value
        end
        hit.TotalDamageDone=final;if evt.Attack then evt.Attack.TotalDamageDone=final end
        return
    end
    context=context or contexts[#contexts];if not context or not context.target or not evt.Hit then return end
    local hit=evt.Hit;local total=0
    for _,pair in ipairs(hit.DamageList) do total=total+math.max(0,pair.Amount) end
    local outgoing=total*multiplier(context)
    local stage=context.eligible and ensureStage(context)
    if context.key=='tianqing_nifeng' then
        local c=casts[context.action]
        if c and E.sameEntity(c.id,context.source) then playNifengLine(c,'BeforeDealDamage') end
    end
    local lineChild=context.key=='internal_yixiantian_hit'
    local lineRoot=lineChild and Line.parent(casts[context.action],true) or nil
    if lineChild and not lineRoot then outgoing=0 end
    if context.key=='taixuan_yixiantian' or lineChild then
        local c=lineChild and lineRoot or casts[context.action]
        if lineChild and not lineRoot then c=nil end
        if c then playYixiantianBeam(c,'BeforeDealDamage') end
        if c and c.position and c.startPosition then
            if not c.lineOrder then
                local p,q=c.startPosition,c.position
                local dx,dz=q[1]-p[1],q[3]-p[3];local length=math.sqrt(dx*dx+dz*dz)
                local finish=length>0 and {p[1]+dx/length*30,q[2],p[3]+dz/length*30} or q
                local targets={}
                for _,target in ipairs(E.nearby(c.id,30,E.enemy)) do
                    local inside,t=R.inLine(E.position(target),p,finish,2)
                    if inside then targets[#targets+1]={id=target,t=t,immune=E.forceImmune(target)} end
                end
                table.sort(targets,function(a,b) return a.t<b.t or a.t==b.t and a.id<b.id end)
                c.lineOrder={};local rank=0
                for _,target in ipairs(targets) do
                    if not target.immune then c.lineOrder[target.id]=rank;rank=rank+1 end
                end
            end
            if E.forceImmune(context.target) or lineChild and c.lineOrder[context.target]==nil then outgoing=0
            else
                local raw=hit.Damage and hit.Damage.TotalDamage or total
                if context.functorUuid then
                    c.lineDamageParts=c.lineDamageParts or {}
                    -- Share the native roll, never the first target's mark bonuses.
                    c.lineDamageParts[context.functorUuid]=c.lineDamageParts[context.functorUuid] or raw
                    outgoing=c.lineDamageParts[context.functorUuid]*multiplier(context)
                elseif spec.spells[c.key] and spec.spells[c.key].base=='AUTO' then
                    -- AUTO requires the documented native identity. Do not match
                    -- different same-type components by order or invent a reroll.
                    outgoing=0
                    if not c.lineIdentityMissing then E.log('Missing native FunctorUuid for AUTO one-line damage');c.lineIdentityMissing=true end
                else
                    -- Compatibility with the previous one-combined-functor form.
                    c.lineDamage=c.lineDamage or raw*multiplier(context);outgoing=c.lineDamage
                end
                outgoing=outgoing*(.5^(c.lineOrder[context.target] or 0))
            end
        end
    end
    if stage then
        stage.outgoingFloat=stage.outgoingFloat+outgoing
        local cumulative=math.floor(stage.outgoingFloat+1e-9)
        outgoing=cumulative-stage.outgoingEmitted;stage.outgoingEmitted=cumulative
    end
    -- TQ ultimate ally/neutral quarter damage is defined natively before saves;
    -- multiplying it here again would incorrectly reduce it to one sixteenth.
    local final,credited=defense(context.target,outgoing,context.key=='taixuan_yixiantian' or lineRoot~=nil,context.transfer,hit.DamageList,stage)
    context.final,context.credited,context.reduced=final,credited,final<outgoing
    trace('BeforeDealDamage',{source=context.source,target=context.target,action=context.action,spell=context.spell,
        hp=E.hp(context.target),temporaryHp=E.tempHp(context.target),nativeTotal=total,outgoing=outgoing,final=final,credited=credited})
    local remaining=final
    for i,pair in ipairs(hit.DamageList) do
        local nextAmount=i==#hit.DamageList and remaining or total>0 and math.floor(final*math.max(0,pair.Amount)/total) or 0
        pair.Amount=nextAmount;remaining=remaining-nextAmount
    end
    hit.TotalDamageDone=final;if evt.Attack then evt.Attack.TotalDamageDone=final end
end
local function flushStage(source,action,target)
    local name=stageKey(source,action,target);local stage=stages[name];if not stage then return end
    stages[name]=nil
    if stage.branch=='xueyan' and stage.eligible and stage.damage>0 and E.enemy(source,target) then
        local s=state(source);local heal,yuan,shield=R.siphon(stage.level,stage.damage,E.maxHp(source),s.shield)
        E.heal(source,heal);E.restore(source,yuan);s=state(source);s.shield=shield;s.shieldUntil=s.turn+2;save(source,s);E.status(source,'ESC_BLOOD_ROBE',2,source)
    end
    local _,branch=E.class(target)
    if branch=='xueyan' then addFrenzy(target,R.frenzyGained(math.max(0,stage.hp-E.hp(target)),E.maxHp(target),false)) end
end
local function afterDamage(evt,context)
    context=context or contexts[#contexts];if not context or not context.target then return end
    trace('DealtDamage',{source=context.source,target=context.target,action=context.action,hp=E.hp(context.target),
        temporaryHp=E.tempHp(context.target),final=context.final,credited=context.credited})
    if diagnostics.enabled then
        local target,action=context.target,context.action
        Ext.Timer.WaitFor(1,function() trace('DamageAfterTick',{target=target,action=action,hp=E.hp(target),temporaryHp=E.tempHp(target)}) end)
    end
    local stage=ensureStage(context)
    stage.damage=stage.damage+(context.credited or evt.Result and evt.Result.Hit.TotalDamageDone or 0)
    local c=casts[context.action]
    if c and not context.transfer then
        if c.key=='internal_taiqing_pulse' then bindPendingHelper(c,context.target) end
        c.targets[context.target]=true;Rain.Capture(c,context.target)
        if context.direct then c.directDamage=true end
    end
    if not context.key and not context.eligible then flushStage(context.source,context.action,context.target) end
end
local function mark(target,kind,owner)
    if not E.character(target) then return end
    owner=actorId(owner)
    local s=state(target);local source=state(owner);if not s or not source then return end
    -- A real recast resets every alias of this owner's old mark together.
    for _,key in ipairs(markKeys(s,kind,owner)) do s.marks[key]=nil end
    s.marks[kind..':'..owner]=kind=='followup' and R.recastFollowup(source.turn) or {expires=source.turn+3,used={}}
    save(target,s);E.status(target,kind=='followup' and 'ESC_FOLLOWUP' or 'ESC_WEAKPOINT',3,owner)
    if kind=='followup' then playSchoolVisual(target,'xingge_wenlu_mark') end
    if kind=='weakpoint' then
        local condition="IF(HasStatus('ESC_WEAKPOINT',context.Target,context.Source))"
        local boosts={condition..':RollBonus(Attack,2)'}
        for _,damageType in ipairs({'Slashing','Piercing','Bludgeoning','Acid','Cold','Fire','Force','Lightning','Necrotic','Poison','Psychic','Radiant','Thunder'}) do
            boosts[#boosts+1]=condition..':IgnoreResistance('..damageType..',Resistant)'
        end
        E.setBoosts(owner,'weakpoint',table.concat(boosts,';'))
    else
        for _,ally in ipairs(recipients(owner,1000,false)) do
            syncFollowupBoostAliases(ally)
            E.setBoosts(ally,'followup_'..owner,followupBoost(owner))
        end
    end
end
local function resonance(c,target)
    if c.key=='internal_resonance' or c.meta.resonance then return end
    local source=actorId(c.id);target=actorId(target)
    for owner in pairs(watchedActors()) do
        local domain=validDomain(owner,'xingge_zhangjian')
        if domain then domain.used=actorUses(domain.used) end
        if domain and E.enemy(owner,target) and (source==owner or E.friend(owner,source)) and E.distance(owner,source)<=6
            and E.allowed(owner,'xingge',true) and not domain.used[source] then
            domain.used[source]=true;local s=state(owner);s.domains.xingge_zhangjian=domain;save(owner,s)
            local victims,seen={target},{[target]=true}
            for other in pairs(c.targets) do
                other=actorId(other)
                if not seen[other] and E.enemy(owner,other) and E.distance(target,other)<=3 then
                    victims[#victims+1]=other;seen[other]=true
                end
            end
            for _,victim in ipairs(victims) do helper(owner,'internal_resonance',victim,{resonance=true,rewardToken=tostring(c.action)..':'..source}) end
        end
    end
end
local function hit(source,target,action)
    source,target=actorId(source),actorId(target)
    flushStage(source,action,target)
    local c=casts[action];if not c or c.tiandiAbandoned then return end
    if c.key=='internal_yixiantian_hit' then
        bindPendingHelper(c,target)
        local root=Line.parent(c,true)
        if root then
            root.targets[target]=true;root.lineHits[target]=true;c.lineHitSeen=true
            Line.complete(c,false)
        end
        return
    end
    -- Immediate resonance helpers can complete before their target callback.
    -- A real hit supplies the same target boundary if its marker arrives first.
    if c.key=='internal_resonance' then bindPendingHelper(c,target) end
    if c.key~='tianqing_tianjian' then CastVfx.Impact(c) end
    if c.meta.tiandiToken and c.key=='internal_tiandi_stage' then
        local entry,s=tiandiEntry(source,c.meta.tiandiToken)
        local ledger=tiandiLedger(entry,target)
        if ledger then ledger.controlAttempted=true;save(source,s) end
    end
    c.targets[target]=true
    -- Item hits still settle damage and contact visuals above. They cannot
    -- acquire character marks or consume/reward an ally's coordinated hit.
    if not E.character(target) then return end
    if not c.firstHits[target] then
        c.firstHits[target]=true
        if c.key=='taixuan_zhaoxi' then mark(target,'weakpoint',source) elseif c.key=='xingge_wenlu' then mark(target,'followup',source) end
    end
    local rewards={}
    for owner in pairs(watchedActors()) do
        local followup=E.friend(owner,source) and activeMark(target,'followup',owner)
        if followup and R.followup(followup,source) then
            local s=state(target);s.marks['followup:'..owner]=followup;save(target,s);rewards[owner]=true
            playSchoolVisual(target,'xingge_wenlu_mark')
        end
    end
    if c.meta.cooperator then rewards[actorId(c.meta.cooperator)]=true end
    c.rewards=actorUses(c.rewards)
    for owner in pairs(rewards) do if not c.rewards[owner] then E.restore(owner,R.cooperation(E.class(owner)));c.rewards[owner]=true end end
    if c.key=='internal_resonance' then
        local s=state(source);s.resonanceRewards=s.resonanceRewards or {}
        -- Every victim in one echo shares its root token. An unbound helper is
        -- not evidence of a separate reward and must not mint one per action.
        if c.meta.rewardToken and R.once(s.resonanceRewards,c.meta.rewardToken) then E.restore(source,R.cooperation(E.class(source))) end
        save(source,s)
    elseif not c.resonanceScheduled then
        c.resonanceScheduled=true
        Ext.Timer.WaitFor(1,function() resonance(c,c.target and c.targets[c.target] and E.enemy(c.id,c.target) and c.target or target) end)
    end
end
function Line.settle(root)
    -- All native targets are present before the root's single reward/echo pass.
    if root.lineSettled then return end
    root.lineSettled=true
    for _,target in ipairs(root.lineTargets) do
        if root.lineHits[target] then hit(root.id,target,root.action) end
    end
end
local function controlFailed(target,marker,source,action)
    local c=casts[action]
    if action==0 and marker=='ESC_SAVEFAIL_TIANQING_TIANJIAN' then
        -- CreateExplosion sends this failed-save status asynchronously with
        -- action 0. The unique native marker already proves this skill's
        -- Strength failure, source and victim; no parent-cast guess is needed.
        local level,branch=E.class(source)
        if level==0 or branch~='tianqing' then return false end
        c={id=source,key='tianqing_tianjian',alias={},meta={}}
    end
    if not c or c.tiandiAbandoned then return false end
    if c.meta.tiandiToken and not tiandiEntry(source,c.meta.tiandiToken) then return false end
    local row=spec.spells[c.alias.parent or c.key]
    if c.meta.parentAction and casts[c.meta.parentAction] then c=casts[c.meta.parentAction] end
    local control=row and row.hitControl
    if not control or control.marker~=marker or not E.enemy(source,target) then return false end
    if c.key=='tianqing_tiandi' then target=E.uuid(E.entity(target)) or target end
    c.controlApplied=c.controlApplied or {}
    if c.key=='tianqing_tiandi' and c.controlApplied[target] then return false end
    c.controlApplied[target]=true
    if c.tianqingToken then
        local ownerState=state(source);local entry=ownerState and ownerState.tianqingStages and ownerState.tianqingStages[c.tianqingToken]
        if entry then entry.controlApplied=c.controlApplied;save(source,ownerState) end
    end
    local s,owner=state(target),state(source)
    s.debuffs[source..':'..c.key]={owner=source,expires=owner.turn+(control.duration or 1),
        ac=(not control.mainOnly or E.sameEntity(c.target,target)) and control.ac or nil,attack=control.attack,slow=control.slow}
    save(target,s)
    if control.prone then E.status(target,'PRONE',1,source) end
    updateAuras();return true
end
local function finishCast(id,spell,action)
    local c=casts[action] or beginCast(id,spell,action,id)
    if c.finished or c.failed then return end;c.finished=true;updateAttackFocus(c);castEffect(c);settleSupportReward(c);Rain.Finish(c);CastVfx.Finish(c)
    playYixiantianBeam(c,'CastedSpellFallback')
    Line.start(c)
    if c.key=='internal_yixiantian_hit' then Line.complete(c,false) end
    playNifengLine(c,'CastedSpellFallback')
    finishTiandiHelper(c,false)
    if c.key=='tianqing_tiandi' then startTiandi(c)
    elseif c.alias.hand and not c.alias.internal and not CastVfx.Enabled(c) then
        if c.key=='tianqing_wanjun' then playTianqing(c,c.areaCenter or c.position or c.targetPosition)
        elseif c.key=='tianqing_lietian' then playTianqing(c,E.position(c.primaryTarget or c.target))
        elseif c.key=='tianqing_bafang' then playTianqing(c,E.position(c.id)) end
    end
    if E.allowed(id,c.branch,false) and (c.key=='xingge_wenlu' or c.branch=='xingge' and c.basicSword) then E.restore(id,R.normalRecovery(E.class(id))) end
    for target in pairs(c.targets) do flushStage(id,action,target) end
    if c.snapshot and c.snapshot.spent>0 then scopedBoosts(id,'cast_snapshot_',0,0) end
    E.setBoosts(id,'cast_weapon_accuracy','')
    local chain=c.alias.chain or (c.alias.continuation and (c.key=='xueyan_wusheng' and 'wusheng' or 'liancheng'))
    if chain then
        local s=state(id)
        if not c.alias.continuation then s.chains[chain]={remaining=c.alias.startChain and 4 or chain=='wusheng' and 5 or 3,snapshot=chain=='wusheng' and c.snapshot or nil}
        elseif s.chains[chain] then s.chains[chain].remaining=s.chains[chain].remaining-1 end
        local entry=s.chains[chain];save(id,s)
        local status=spec.chainStatuses and spec.chainStatuses[chain] or (chain=='wusheng' and 'ESC_CHAIN_WUSHENG' or 'ESC_CHAIN_LIANCHENG')
        if entry and entry.remaining>0 then
            E.status(id,status,-1,id)
            if chain=='liancheng' then E.setResource(id,spec.chainMoveResource,6) end
        else s.chains[chain]=nil;save(id,s);E.removeStatus(id,status,id);E.setResource(id,spec.chainMoveResource,0) end
    end
    -- Native OnCast passives grant continuation charges only after an actual
    -- ActionPoint payment. Native UseCosts consumes subsequent charges.
    -- Projectile callbacks can be later than CastedSpell. Do not discard their snapshot.
    scheduleCastRetirement(c)
end
local function turnStarted(id)
    for ally,queue in pairs(cooperationRequests) do
        for i=#queue,1,-1 do if E.sameEntity(queue[i].owner,id) then table.remove(queue,i) end end
        sendCooperation(ally)
    end
    -- Session refresh uses UUIDs; Osiris can later watch the same owner as
    -- Name_GUID. One victim turn receives one pulse per actual owner.
    local aftershockOwners={}
    for owner in pairs(watched) do
        local identity=E.uuid(E.entity(owner)) or owner
        if not aftershockOwners[identity] then
            aftershockOwners[identity]=true
            if validDomain(owner,'tianqing_tianjian') and E.enemy(owner,id) and E.distance(owner,id)<=6 then helper(owner,'internal_aftershock',id) end
        end
    end
    if E.class(id)==0 and not watched[actorId(id)] then return end
    local s=state(id);if not s then return end
    s.turn=s.turn+1;s.autoReleased=false;s.resonanceRewards={}
    for key,domain in pairs(s.domains) do if not R.tickDuration(domain,s.turn) then s.domains[key]=nil else domain.used={} end end
    -- Native StatusRemoved ends guard, including real-time expiry outside combat.
    if s.shieldUntil and s.shieldUntil<=s.turn then s.shield=0 end
    save(id,s)
    clearContinuous(id)
    E.setResource(id,spec.chainMoveResource,0);E.setResource(id,spec.flightResource,0)
    E.removeStatus(id,'ESC_CHAIN_LIANCHENG',id);E.removeStatus(id,'ESC_CHAIN_WUSHENG',id);E.removeStatus(id,'ESC_IN_FLIGHT',id)
    s=state(id);s.chains={};save(id,s)
    local level,branch=E.class(id)
    if level>0 and branch=='taixuan' and E.allowed(id,branch,false) then E.restore(id,R.breath(level,branch,false,true));E.heal(id,E.maxHp(id)*(level>=11 and .06 or .05),true) end
    updateAuras();refresh(id);updateRescue(id)
    if validDomain(id,'taixuan_taiqing') then scheduleDomainTurnPulse(id,'taixuan_taiqing') end
    if validDomain(id,'xueyan_xuehai') then scheduleDomainTurnPulse(id,'xueyan_xuehai') end
end
local function killed(target,source,action)
    local level,branch=E.class(source);local c=casts[action]
    if branch~='xueyan' or not c or c.failed or not E.allowed(source,branch,false) or not (offensiveKey(c.key) or c.swordDamage) or not E.enemy(source,target) then return end
    state(source) -- Migrate an old save's historical ledger before any new reward.
    local victim=E.entity(target);if not victim then return end
    local receipts=victim.Vars.ESC_BloodKillReceipts or {}
    if R.once(receipts,actorId(source)) then
        victim.Vars.ESC_BloodKillReceipts=receipts
        local heal,yuan,frenzy=R.killReward(level,E.maxHp(source));E.heal(source,heal);E.restore(source,yuan);addFrenzy(source,frenzy)
    end
end
local function statusAttempt(id,status,source,action)
    trace('StatusAttempt',{target=id,status=status,source=source,action=action,alreadyApplied=E.hasStatus(id,status)})
    local level,branch=E.class(id)
    local stat=Ext.Stats.Get(status,nil,false)
    local incap=isControlled(status) and stat and stat.StatusType=='INCAPACITATED'
    if level<4 or branch=='xingge' or not E.allowed(id,branch,false) or not (critical[status] or incap) then return false end
    local s=state(id);if s.autoReleased or not E.spendResource(id,E.reaction,1) then return false end
    s.autoReleased=true;save(id,s)
    -- Patch 8 provides no PreventStatusApply Osiris call. The live ordering of this
    -- attempt-time temporary immunity remains an explicit integration contract.
    E.setBoosts(id,'auto_release','StatusImmunity('..status..')')
    trace('AutomaticRelease',{target=id,status=status,source=source,action=action})
    Ext.Timer.WaitFor(1,function()
        trace('ReleaseAfterNativeAttempt',{target=id,status=status,applied=E.hasStatus(id,status)})
        E.setBoosts(id,'auto_release','')
    end);return true
end
local function counterEligible(id,source,action)
    local s=state(id);local c=casts[action]
    if not s or not s.guard or s.guard.rank<2 or not E.hasStatus(id,'ESC_COUNTER_READY') then return false end
    if c and (c.key=='internal_counter2' or c.key=='internal_counter3') then return false end
    return E.alive(id) and E.allowed(id,'taixuan',false) and E.enemy(id,source) and E.distance(id,source)<=18 and E.visible(id,source)
end
local function counter(id,source,action)
    if not counterEligible(id,source,action) then return false end
    return helper(id,state(id).guard.rank==3 and 'internal_counter3' or 'internal_counter2',source,{counter=true})
end
local function decay()
    for id in pairs(watched) do local _,branch=E.class(id);if branch=='xueyan' and not E.combat(id) then local s=state(id);if s.frenzy>0 then addFrenzy(id,-1) end end end
end
local function refreshClassActors(resetTransient)
    for _,entity in ipairs(Ext.Entity.GetAllEntitiesWithComponent('Classes')) do local id=E.uuid(entity);if id then
        -- Save-loaded beneficiaries may have no sword class and have not been
        -- watched this session. Reconcile their persisted visual statuses too.
        for _,visual in ipairs(partyDomainVisuals) do
            if E.hasStatus(id,visual.status) then auraVisualTargets[id]=true end
        end
        refresh(id)
        if resetTransient and E.class(id)>0 then
            scopedBoosts(id,'cast_snapshot_',0,0);E.setBoosts(id,'cast_weapon_accuracy','')
        end
    end end
end
local function refreshNewAvatar(avatar)
    local id=E.uuid(E.entity(avatar));if not id then return end
    refresh(id)
    if pendingAvatarRefreshes[id] then return end
    local pending={};pendingAvatarRefreshes[id]=pending
    local generation=timerGeneration
    -- A joining player's Classes/equipment may be published after its avatar
    -- event. Retry once; repeated notifications share this bounded retry.
    Ext.Timer.WaitFor(200,function()
        if generation~=timerGeneration or pendingAvatarRefreshes[id]~=pending then return end
        pendingAvatarRefreshes[id]=nil
        if E.entity(id) then refresh(id) end
    end)
end
local function sessionLoaded()
    nativeHeals={};nativeHealOrder={};pendingWindHealing={};healingContexts={}
    CastVfx.Reset()
    for _,c in pairs(casts) do Rain.Cancel(c);Line.cancel(c);c.yixiantianBeamCancelled=true;c.nifengLineCancelled=true;c.xiangfuActualHealConfirmed=nil end
    rescueRequests={};cooperationRequests={};pendingAvatarRefreshes={};pendingWeaponWisdom={}
    pendingDomainTurnPulses={}
    tiandiDispatch=nil
    Line.dispatch=nil
    tianqingTimerHandles={}
    -- Persistent timer payloads resume unfinished steps. Do not restart a
    -- saved cast or replay a sword which was already emitted before saving.
    for action,c in pairs(casts) do if c.tianqingToken or c.meta and c.meta.tiandiToken then casts[action]=nil end end
    timerGeneration=timerGeneration+1;local generation=timerGeneration
    -- Native status durations also run in real time outside combat. A saved
    -- turn counter must not restore a domain after its native status expired.
    -- SessionLoaded is deferred until Osiris and status containers are ready.
    for _,entity in pairs(Ext.Entity.GetAllEntitiesWithComponent('Classes')) do
        local id=E.uuid(entity);local s=entity.Vars.ESC_State
        if id and s and s.domains then
            for key,status in pairs(domainStatuses) do
                if s.domains[key] and not E.hasStatus(id,status) then endDomain(id,key) end
            end
        end
    end
    refreshClassActors(true)
    -- SessionLoaded is deferred until saved spell books are available. Missing
    -- old-save grants are repaired once here, never during a new progression.
    for _,entity in ipairs(Ext.Entity.GetAllEntitiesWithComponent('Classes')) do
        local id=E.uuid(entity);if id then repairSavedBonusTechnique(id) end
    end
    -- Include saved beneficiaries without a sword class. Seed old aura targets
    -- so the normal range/expiry reconciliation can discard obsolete bonuses
    -- before restoring the remaining native boosts from persisted descriptions.
    local boostActors={}
    for _,entity in ipairs(Ext.Entity.GetAllEntitiesWithComponent('Health')) do
        local id=E.uuid(entity);local s=entity.Vars.ESC_State
        if id and (s or E.hasStatus(id,'ESC_CONTROL_RESISTANCE')) and not boostActors[id] then
            s=s or state(id)
            boostActors[id]=true;watched[id]=true
            for slot,value in pairs(s.boosts or {}) do
                if slot=='aura' and value~='' then auraTargets[id]=auraTargets[id] or {} end
                if slot=='auto_release' or slot=='cast_weapon_accuracy' or slot:find('cast_snapshot_',1,true)==1 then
                    E.setBoosts(id,slot,'')
                end
            end
            if E.class(id)==0 then syncReceivedControlResistance(id) end
            -- Static conditional beneficiary boosts no longer need a polling
            -- watch. Normalize old saved owner aliases once during restoration.
            syncFollowupBoostAliases(id)
        end
    end
    updateAuras()
    for id in pairs(boostActors) do E.restoreBoosts(id) end
    for _,entity in pairs(Ext.Entity.GetAllEntitiesWithComponent('Classes')) do
        local id=E.uuid(entity);local s=entity.Vars.ESC_State
        for token,entry in pairs(s and s.tianqingStages or {}) do
            local orphaned=false
            for _,ledger in pairs(entry.targetLedger or {}) do
                if ledger.inFlight and not ledger.inFlight.action then orphaned=true;break end
            end
            if orphaned then
                -- Old saves can contain a delivered attack without its action
                -- binding. Neither replay nor completion is provable: retire it.
                E.log('Cancelled saved Tianqing cast with an unbound native attack: '..token)
                cancelTiandi(id,token)
            else
                tiandiParent(id,entry,token)
                for target,ledger in pairs(entry.targetLedger or {}) do
                    local flight=ledger.inFlight
                    if flight and flight.action then
                        local c={id=id,key=flight.key,spell=flight.spell,action=flight.action,target=target,
                            alias=aliases[flight.spell] or {},meta=flight.meta,level=E.class(id),branch='tianqing',
                            targets={},firstHits={},rewards={},helperMetaBound=true,finished=flight.finished or false,failed=flight.failed or false}
                        casts[flight.action]=c
                        if flight.finished then Ext.Timer.WaitFor(1,function() if generation==timerGeneration then completeTiandiHelper(c) end end) end
                    else dispatchTiandiTarget(id,entry,token,target) end
                end
                finishTiandiIfIdle(id,entry,token)
            end
        end
    end
    if not (Ext.Timer.WaitForPersistent and Ext.Timer.RegisterPersistentHandler) then
        -- Older SE builds use the saved checkpoint with ordinary game-clock
        -- timers. Restart only the pending delay (at most one stage interval),
        -- never its already emitted sword or a committed attack stage.
        for _,entity in pairs(Ext.Entity.GetAllEntitiesWithComponent('Classes')) do
            local id=E.uuid(entity);local s=entity.Vars.ESC_State
            for token,entry in pairs(s and s.tianqingStages or {}) do
                local pending=entry.pending
                if pending then scheduleTiandi(pending.delayMs,{id=id,token=token,stage=pending.stage,kind=pending.kind}) end
            end
        end
    end
    local function periodic()
        if generation~=timerGeneration then return end
        updateAuras();for id in pairs(watched) do if E.class(id)>0 then updateRescue(id) end end
        Ext.Timer.WaitFor(200,periodic)
    end
    local function frenzyDecay() if generation~=timerGeneration then return end;decay();Ext.Timer.WaitFor(6000,frenzyDecay) end
    Ext.Timer.WaitFor(200,periodic);Ext.Timer.WaitFor(6000,frenzyDecay)
    E.log('Server bridge loaded; native/UI/game verification is required for engine contracts.')
end
Ext.Events.DealDamage:Subscribe(function(evt)
    healingInterference(evt.Target)
    local source,target=E.uuid(E.entity(evt.Caster)),E.uuid(E.entity(evt.Target))
    local spell=E.spellName(evt.SpellId) or evt.Hit and evt.Hit.SpellId;local key=keyFor(spell);local level,branch=E.class(source)
    local status=evt.Hit and evt.Hit.StatusId
    local weapon=evt.HitWith=='Weapon' or evt.Hit and evt.Hit.HitWith=='Weapon' or basicSwordAttacks[spell]
    local offhand=spell=='Target_OffhandAttack' or spell=='Projectile_OffhandAttack'
        or spell=='Target_OffHandAttack' or spell=='Projectile_OffHandAttack' or evt.Hit and evt.Hit.CauseType=='Offhand'
    local original=spell and spell:gsub('^ESC_FREE_','')
    local ranged=original=='Projectile_MainHandAttack' or original=='Projectile_OffhandAttack' or original=='Projectile_OffHandAttack'
        or evt.Hit and evt.Hit.SpellAttackType=='RangedWeaponAttack'
    local thrown=evt.Hit and evt.Hit.Throwing and E.uuid(E.entity(evt.Hit.Throwing))
    local sword=thrown and E.isSword(thrown) or not ranged and E.sword(source,offhand)
    local eligible=source and E.allowed(source,branch,false) and (offensiveKey(key) or level>0 and sword~=nil and sword~=false and weapon) and (status==nil or status=='')
    local transferred=pendingTransfer~=nil
    if transferred then eligible=false;key=nil;spell=nil end
    -- Immediate Target helpers may deal damage and send hit/save markers before
    -- UsingSpell. Bind the actual target here so control and queue completion
    -- share the same native action, regardless of callback order.
    if source and target and (isTiandiHelper(key) or key=='internal_yixiantian_hit') then beginCast(source,spell,evt.StoryActionId,target) end
    local c=casts[evt.StoryActionId];if c and eligible then c.swordDamage=true end
    if c and not transferred and (status==nil or status=='') and c.key~='tianqing_tianjian' then CastVfx.Impact(c) end
    local functorUuid
    if (key=='taixuan_yixiantian' or key=='internal_yixiantian_hit') and evt.Functor then
        local value=tostring(evt.Functor.FunctorUuid or '')
        if value~='' and value~='00000000-0000-0000-0000-000000000000' then functorUuid=value end
    end
    trace('DealDamage',{source=source,target=target,spell=spell,action=evt.StoryActionId,hp=E.hp(target),temporaryHp=E.tempHp(target),eligible=eligible})
    contexts[#contexts+1]={source=source,target=target,key=key,spell=spell,level=level,branch=branch,action=evt.StoryActionId,
        hp=E.hp(target),eligible=eligible,transfer=transferred,functorUuid=functorUuid,direct=spell~=nil and (status==nil or status=='')}
end)
Ext.Events.BeforeDealDamage:Subscribe(function(evt)
    if not pendingTransfer and #contexts==0 then trace('UnpairedBeforeDealDamage',{}) end
    beforeDamage(evt)
end)
Ext.Events.DealtDamage:Subscribe(function(evt) afterDamage(evt);contexts[#contexts]=nil end)
local functorRecipientField={AttackTarget='Target',NearbyAttacked='Target',NearbyAttacking='Target',
    Equip='Target',Move='Target',Target='Source',Source='Source',
    [1]='Target',[3]='Target',[4]='Source',[5]='Target',[6]='Target',[7]='Target',[8]='Source'}
local function functorEntityUuid(ref)
    if not ref then return nil end
    -- Native Caster may already be an entity handle/proxy. Reading .Handle
    -- first can throw before Ext.Entity.Get gets a valid direct reference.
    local ok,entity=pcall(E.entity,ref)
    local id=ok and E.uuid(entity) or nil
    return id or E.refUuid(ref)
end
local function groundFunctorContext(params)
    local flags=params.PropertyContext
    if type(flags)=='number' then return (flags & 16)~=0 end
    return flags and flags.GROUND==true
end
local function functorRecipient(params)
    if not params then return nil end
    -- Params is a tagged variant. Missing proxy properties throw in BG3SE, so
    -- only read fields declared for this concrete FunctorContextType.
    local field=functorRecipientField[params.Type] or functorRecipientField[tostring(params.Type)]
    if not field then return nil end
    local ref=params[field]
    if not ref then return nil end
    local handle=ref
    if type(ref)~='number' and type(ref)~='string' then
        local hasHandle,value=pcall(function() return ref.Handle end)
        if hasHandle and value then handle=value end
    end
    local ok,entity=pcall(E.entity,handle)
    return ok and E.uuid(entity) or nil
end
local function healingProperty(params,name,mask)
    local flags=params and params.PropertyContext
    if type(flags)=='number' then return (flags & mask)~=0 end
    return flags and flags[name]==true
end
local function completedNativeSupport(params,target)
    if not target or not healingProperty(params,'HEAL',262144) then return end
    local source=functorEntityUuid(params.Caster)
    local key=nativeHealKey(source,target,params.StoryActionId)
    local receipt=key and nativeHeals[key];local c=casts[params.StoryActionId]
    if not receipt or receipt.rewardChecked or receipt.ambiguous or not c
        or c.key~='xingge_xiangfu' or c.failed or c.invalid
        or not E.sameEntity(source,c.id) or not E.sameEntity(target,c.target)
        or E.spellName(params.SpellId)~='Target_ESC_xingge_xiangfu' then return end
    receipt.rewardChecked=true
    -- H28 real OnHeal is after the HP write; its TotalHealDone is the rolled
    -- amount (4 even at HP12/12). InitialHPPercentage is rounded, so retain
    -- exact HP for 123/124 as well. Never sample at UsingSpell or next tick.
    local hit=params.Hit
    if hit and (tonumber(hit.TotalHealDone) or 0)>0 and E.hp(target)>receipt.before then
        c.xiangfuActualHealConfirmed=true
    end
end
Ext.Events.ExecuteFunctor:Subscribe(function(evt)
    local context={}
    local params=evt.Params
    -- CreateExplosion is the landing operation even when the area is empty.
    -- Read only fields declared for AttackPosition in Norbyte Functors.h.
    if params and (tostring(params.Type)=='AttackPosition' or params.Type==2) then
        for _,functor in pairs(evt.Functor and evt.Functor.FunctorList or {}) do
            if tostring(functor.TypeId)=='CreateExplosion' and (functor.SpellId=='Projectile_ESC_TianjianImpact' or functor.SpellId=='Projectile_ESC_TianjianImpact_Off')
                and groundFunctorContext(params) then
                local id=functorEntityUuid(params.Caster);local c=casts[params.StoryActionId]
                if id and c and E.sameEntity(c.id,id) and c.key=='tianqing_tianjian' and not c.alias.impact then
                    -- The landing explosion may reuse its parent's action
                    -- or have no independent CastedSpell notification.
                    context.tianjianLanding=c
                    local play=CastVfx.Enabled(c) and CastVfx.Impact or playTianqing
                    local ok,err=pcall(play,c,copyPosition(params.Position))
                    if not ok then E.log('Tianjian landing VFX failed: '..tostring(err)) end
                end
            end
        end
    end
    local target=functorRecipient(params)
    for _,functor in pairs(evt.Functor and evt.Functor.FunctorList or {}) do
        if tostring(functor.TypeId)=='RegainHitPoints' and not tostring(functor.HealingType):find('Regeneration',1,true) then context.healing=true end
    end
    if params and (tostring(params.Type)=='AttackTarget' or params.Type==1) then
        for _,functor in pairs(evt.Functor and evt.Functor.FunctorList or {}) do
            if tostring(functor.TypeId)=='ApplyStatus' and functor.StatusId=='ESC_XIANGFU_HEALED' then
                completedNativeSupport(params,target)
            end
        end
    end
    if context.healing and target then
        context.target=target;context.before=E.hp(target)
        if params and (tostring(params.Type)=='AttackTarget' or params.Type==1)
            and (healingProperty(params,'TARGET',1) or healingProperty(params,'CAST',4) or healingProperty(params,'AOE',2)) then
            context.native=rememberNativeHeal(functorEntityUuid(params.Caster),target,params.StoryActionId,E.spellName(params.SpellId))
        end
    end
    healingContexts[#healingContexts+1]=context
end)
Ext.Events.AfterExecuteFunctor:Subscribe(function(evt)
    local context=healingContexts[#healingContexts];healingContexts[#healingContexts]=nil
    local landing=context and context.tianjianLanding
    if landing and not landing.tianjianLandingApplied and not landing.failed and not landing.invalid then
        local level,branch=E.class(landing.id)
        if level>0 and branch=='tianqing' and E.alive(landing.id) then
            -- Commit before status callbacks: one actual landing starts
            -- one four-round buff, including an empty landing area.
            landing.tianjianLandingApplied=true
            startDomain(landing.id,'tianqing_tianjian')
        end
    end
    if not context or not context.target or context.native then return end
    local gained=E.hp(context.target)-context.before
    local mult=Runtime.HealingMultiplier(context.target)
    if gained>0 and mult>1 then E.heal(context.target,gained*(mult-1),true) end
end)
local function queueNativeHealingBonus(target,amount)
    local pending=pendingWindHealing[target]
    if pending then pending.amount=pending.amount+amount;return end
    pending={amount=amount,generation=timerGeneration};pendingWindHealing[target]=pending
    -- Settlement was already proved by the native receipt. Coalesce earned
    -- bonuses at the event-loop boundary: multiple asynchronous SetHitpoints
    -- calls in one frame would otherwise overwrite each other's absolute HP.
    Ext.OnNextTick(function()
        if pending.generation~=timerGeneration or pendingWindHealing[target]~=pending then return end
        pendingWindHealing[target]=nil
        if E.entity(target) and E.alive(target) then E.heal(target,pending.amount,true) end
    end)
end
-- Official ServerStatusApplyEvent + EsvStatusHeal fields; H28 action75/81/86
-- establishes this callback follows native HP settlement with source/action.
-- No status userdata is retained and no native HEAL fields are overwritten.
Ext.Entity.OnCreate('ServerStatusApplyEvent',function(_,_,component)
    if component.StatusId~='HEAL' then return end
    local target=E.uuid(E.entity(component.Target));if not target then return end
    local entity=E.entity(target);local character=entity and entity.ServerCharacter
    local status=character and character:GetStatus('HEAL')
    if not status or not status.Started then return end
    local source=E.uuid(E.entity(status.StatusSource))
    local key=nativeHealKey(source,target,status.StoryActionID)
    local receipt=key and nativeHeals[key]
    if not receipt then healingInterference(target);return end
    nativeHeals[key]=nil -- Consume before E.heal can create any nested work.
    local amount=tonumber(status.HealAmount) or 0
    local mult=Runtime.HealingMultiplier(target)
    -- Both native and Lua domains must still be active at actual settlement.
    -- Scripted SetHitpoints has no pending Regain receipt and cannot recurse.
    if not receipt.ambiguous and amount>0 and mult>1 and E.hasStatus(target,'ESC_DAMAGE_SHARE') then
        local extra=math.ceil(amount*mult)-amount
        if extra>0 and E.hp(target)<E.maxHp(target) then queueNativeHealingBonus(target,extra) end
    end
end)
Ext.Osiris.RegisterListener('UsingSpell',5,'before',function(id,spell,kind,element,action) local c=beginCast(id,spell,action);CastVfx.Begin(c) end)
Ext.Osiris.RegisterListener('UsingSpellOnTarget',6,'before',function(id,target,spell,kind,element,action) local c=beginCast(id,spell,action,target);Rain.Capture(c,target);CastVfx.Begin(c) end)
Ext.Osiris.RegisterListener('UsingSpellAtPosition',8,'before',function(id,x,y,z,spell,kind,element,action) local c=beginCast(id,spell,action,nil,{x,y,z});CastVfx.Begin(c) end)
Ext.Osiris.RegisterListener('CastedSpell',5,'after',function(id,spell,kind,element,action) finishCast(id,spell,action) end)
Ext.Osiris.RegisterListener('CastSpellFailed',5,'after',function(id,spell,kind,element,action) failedCast(id,spell,action) end)
-- Official MissedBy(Defender,AttackerOwner,Attacker,StoryActionID).
-- Match the direct caster and its existing action; no new cast or failure replay.
Ext.Osiris.RegisterListener('MissedBy',4,'after',function(target,owner,attacker,action)
    local c=casts[action]
    if c and E.sameEntity(c.id,owner) and E.sameEntity(c.id,attacker) then playNifengLine(c,'MissedBy') end
end)
Ext.Osiris.RegisterListener('StatusApplied',4,'after',function(id,status,source,action)
    trace('StatusApplied',{target=id,status=status,source=source,action=action})
    if Osi.IsItem(id)==1 then local owner=Osi.GetOwner(id);if owner and E.class(owner)>0 then refresh(owner) end end
    if status=='ESC_COUNTER_READY' then syncGuard(id,true);refresh(id)
    elseif status=='ESC_XIANGFU_HEALED' then
        -- A positive native marker also fires at full HP. Require the exact
        -- same-action OnHeal receipt above, then match original identities.
        -- Resource settlement remains after native cast cost deduction.
        local c=casts[action];local level,branch=E.class(source)
        if c and c.key=='xingge_xiangfu' and c.xiangfuActualHealConfirmed and not c.failed and not c.invalid and not c.xiangfuRewarded
            and source and E.sameEntity(source,c.id) and E.sameEntity(id,c.target)
            and level>0 and branch=='xingge' and E.allowed(source,branch,false)
            and not E.sameEntity(source,id) and E.friend(source,id) and E.distance(source,id)<=18 then
            c.xiangfuRewarded=true
            cooperation(c,id)
            if c.finished then settleSupportReward(c) end
        end
    elseif status=='ESC_HIT_MARKER' then hit(source,id,action)
    elseif status=='ESC_TIANDI_TARGET' then
        local c=casts[action]
        if c then
            c.tiandiTargets=c.tiandiTargets or {}
            if not c.tiandiTargets[id] then
                c.tiandiTargets[id]=true
                -- New paid roots register victims only. The cast-level clock
                -- dispatches three attacks; legacy data still owns its first.
                if not (spec.tianqingVfx and spec.tianqingVfx.enabled and spec.tianqingVfx.tiandi) then
                    helper(source,'internal_tiandi_stage',id,{parentAction=action,hand=c.alias.hand})
                    helper(source,'internal_tiandi_stage',id,{parentAction=action,hand=c.alias.hand})
                end
            end
        end
    elseif status:find('ESC_SAVEFAIL_',1,true)==1 then controlFailed(id,status,source,action)
    elseif (status=='DOWNED' or status=='DYING' or status=='DEAD') and E.character(id) then cancelWorldSwordLineOwner(id);Rain.CancelOwner(casts,id);CastVfx.CancelOwner(id);cancelTiandi(id);local s=state(id);if s then s.shield=0;s.domains={};save(id,s);clearContinuous(id);setFrenzy(id,0);updateAuras() end end
    if status=='ESC_CONTROL_RESISTANCE' and E.class(id)==0 then syncReceivedControlResistance(id) end
    if E.class(id)>0 then
        if status=='ESC_CONTROL_RESISTANCE' then refresh(id) end
        updateRescue(id)
    end
end)
Ext.Osiris.RegisterListener('StatusRemoved',4,'after',function(id,status,source,action)
    if domainKeys[status] and not E.hasStatus(id,status) then
        -- A delayed removal from an old application must not end a recast.
        -- Clearing only the domain leaves Blood Robe's siphon shield intact.
        endDomain(id,domainKeys[status]);updateAuras()
    elseif (status=='ESC_FOLLOWUP' or status=='ESC_WEAKPOINT') and not E.hasStatus(id,status) then
        local entity=E.entity(id);local s=entity and entity.Vars.ESC_State
        local prefix=status=='ESC_FOLLOWUP' and 'followup:' or 'weakpoint:'
        local changed=false
        for key in pairs(s and s.marks or {}) do
            if key:sub(1,#prefix)==prefix then s.marks[key]=nil;changed=true end
        end
        if changed then save(id,s) end
    elseif status=='ESC_COUNTER_READY' and not E.hasStatus(id,status) then
        local s=state(id);if s then s.guard=nil;save(id,s) end
        -- Leave rank markers on their native clock: an old Ready removal
        -- can be delivered after a new rank is applied during refresh.
        if E.class(id)>0 then refresh(id) end
    elseif status=='ESC_EXTRA_ATTACK' and not E.hasStatus(id,status) then
        clearContinuous(id)
    elseif status=='ESC_XINGGE_PROTECTION' then
        local s=state(id)
        if s then
            for key,p in pairs(s.protections) do
                if p.kind=='huifeng' and (not E.hasStatus(id,status) or E.sameEntity(p.owner,source) and p.action==action) then s.protections[key]=nil end
            end
            save(id,s);updateAuras()
        end
    end
    if Osi.IsItem(id)==1 then local owner=Osi.GetOwner(id);if owner and E.class(owner)>0 then refresh(owner) end end
    if status=='ESC_CONTROL_RESISTANCE' then
        if E.class(id)>0 then refresh(id) else syncReceivedControlResistance(id) end
    end
end)
Ext.Osiris.RegisterListener('StatusAttempt',4,'before',statusAttempt)
Ext.Osiris.RegisterListener('KilledBy',4,'after',function(target,owner,attacker,action) killed(target,owner,action) end)
-- Installed Patch 8 story_header.div: Resurrected((CHARACTER)_Character).
Ext.Osiris.RegisterListener('Resurrected',1,'after',function(id)
    local entity=E.entity(id)
    if entity and entity.Vars.ESC_BloodKillReceipts~=nil then entity.Vars.ESC_BloodKillReceipts=nil end
end)
Ext.Osiris.RegisterListener('AttackedBy',7,'after',function(target,owner,attacker,damageType,amount,cause,action)
    local c=casts[action]
    if c and not c.key and c.directDamage then hit(owner,target,action) end
end)
Ext.Osiris.RegisterListener('TurnStarted',1,'after',turnStarted)
Ext.Osiris.RegisterListener('LeftCombat',2,'after',function(id,combat) cancelWorldSwordLineOwner(id);Rain.CancelOwner(casts,id);CastVfx.CancelOwner(id);cancelTiandi(id);if E.class(id)>0 then clearContinuous(id) end end)
Ext.Osiris.RegisterListener('LeveledUp',1,'after',refresh)
Ext.Osiris.RegisterListener('RespecCompleted',1,'after',function(id) refresh(id);updateAuras() end)
Ext.Osiris.RegisterListener('Equipped',2,'after',function(item,id) refresh(id);updateAuras() end)
Ext.Osiris.RegisterListener('Unequipped',2,'after',function(item,id) refresh(id);updateAuras() end)
-- New-game character creation can finish after SessionLoaded and its initial
-- equipment events. Discover the finalized actors when gameplay is ready.
Ext.Osiris.RegisterListener('LevelGameplayReady',2,'after',function() refreshClassActors(false) end)
Ext.Osiris.RegisterListener('UserAvatarCreated',3,'after',function(user,avatar,guardian) refreshNewAvatar(avatar) end)
Ext.Events.SessionLoaded:Subscribe(function()
    -- SessionLoaded can run while Osiris is restricted. Reacquire actors on the
    -- next engine tick; do not carry scoped entity userdata across that boundary.
    pendingSessionLoad=pendingSessionLoad+1;local pending=pendingSessionLoad
    Ext.OnNextTick(function() if pending==pendingSessionLoad then sessionLoaded() end end)
end)
Ext.Events.NetMessage:Subscribe(function(evt)
    if evt.Channel~='ESC_ControlRescueIntent' and evt.Channel~='ESC_CooperationIntent' then return end
    local ok,data=pcall(Ext.Json.Parse,evt.Payload);if not ok then return end
    if type(data)=='table' and type(data.id)=='string' and type(data.token)=='number' then
        if evt.Channel=='ESC_ControlRescueIntent' then rescue(data.id,data.token,evt.UserID)
        elseif type(data.spell)=='string' then chooseCooperation(data.id,data.token,data.spell,evt.UserID) end
    end
end)
Runtime.Refresh,Runtime.State,Runtime.BeginCast,Runtime.FinishCast=refresh,explicitState,beginCast,finishCast
Runtime.TrackState=retireEmptyState
Runtime.Hit,Runtime.BeforeDamage,Runtime.AfterDamage,Runtime.TurnStarted=hit,beforeDamage,afterDamage,turnStarted
Runtime.UpdateAuras,Runtime.Decay,Runtime.StatusAttempt,Runtime.SessionLoaded=updateAuras,decay,statusAttempt,sessionLoaded
Runtime.CounterEligible,Runtime.Counter,Runtime.FlushStage,Runtime.Defense=counterEligible,counter,flushStage,defense
Runtime.Killed,Runtime.Pulse=killed,pulse
Runtime.ControlRescue,Runtime.UpdateRescue=rescue,updateRescue
Runtime.ControlFailed=controlFailed
Runtime.CooperationChoice=chooseCooperation
Runtime.StartDiagnostics=function() diagnostics={enabled=true,events={}};return true end
Runtime.Diagnostics=function() return diagnostics.events end
Runtime.WriteDiagnostics=function(path)
    diagnostics.enabled=false
    return Ext.IO.SaveFile(path or 'EasternSwordCultivator/runtime-contract.json',Ext.Json.Stringify(diagnostics.events))
end
Runtime.HealingMultiplier=function(id)
    if validDomain(id,'xingge_fengyu') then return E.class(id)>=10 and 1.75 or 1.50 end
    return 1
end
ESC.Runtime,ESC.Refresh,ESC.State=Runtime,refresh,explicitState
