-- Server bridge: native spells own targeting/dice/saves; this file owns clocks,
-- source-specific rewards, snapshots and final damage. See runtime contract report.
local R,E=ESC.Rules,ESC.Engine
local spec=Ext.Json.Parse(Ext.IO.LoadFile('Mods/EasternSwordCultivator_6560ea02-fe1e-5fdb-8631-b41a2e53af90/ScriptExtender/Lua/GeneratedSpec.json','data'))
E.resource,E.classes=spec.resource,spec.classes
local Runtime={}
local keys,aliases={},spec.aliases or {}
for key,row in pairs(spec.spells) do keys[row.stat]=key end
for spell,alias in pairs(aliases) do keys[spell]=alias.key end
local helpers={internal_taiqing_pulse='Target_ESC_TaiqingPulse',internal_blood_pulse='Target_ESC_BloodPulse',
    internal_counter2='Target_ESC_Counter2',internal_counter3='Target_ESC_Counter3',
    internal_resonance='Target_ESC_Resonance',internal_aftershock='Target_ESC_Aftershock',
    internal_tiandi_stage='Target_ESC_TiandiStage',internal_tianbeng_main='Target_ESC_TianbengMain',
    internal_chengfeng_burst='Target_ESC_ChengfengBurst',internal_huifeng_control='Target_ESC_HuifengControl',
    internal_liuguang_stage='Target_ESC_LiuguangStage',internal_tianbeng_cone='Target_ESC_TianbengCone'}
for key,spell in pairs(helpers) do keys[spell]=key end
E.classSpellKeys=keys
local basicSwordAttacks={Target_MainHandAttack=true,Target_OffHandAttack=true,
    Projectile_MainHandAttack=true,Projectile_OffHandAttack=true,
    Target_OffhandAttack=true,Projectile_OffhandAttack=true}
local watched,casts,contexts,pendingHelpers,stages={}, {}, {}, {}, {}
local auraTargets,sequence,timerGeneration={},0,0
local rescueRequests={}
local cooperationRequests={}
local pendingAvatarRefreshes={}
local healingContexts={}
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
local function state(id)
    local entity=E.entity(id)
    if not entity then return nil end
    local s=entity.Vars.ESC_State
    if not s then s={turn=0,frenzy=0,shield=0,damageMode='Necrotic',qiSword=false,boosts={},domains={},kills={},marks={},protections={}} end
    s.turn=s.turn or 0;s.frenzy=s.frenzy or 0;s.shield=s.shield or 0;s.damageMode=s.damageMode or 'Necrotic'
    s.marks=s.marks or {};s.protections=s.protections or {};s.domains=s.domains or {};s.kills=s.kills or {};s.boosts=s.boosts or {};s.chains=s.chains or {};s.debuffs=s.debuffs or {}
    entity.Vars.ESC_State=s;watched[id]=true
    return s
end
local function save(id,s) local entity=E.entity(id);if entity then entity.Vars.ESC_State=s end end
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
        or key=='internal_aftershock' or key=='internal_tiandi_stage' or key=='internal_tianbeng_main'
        or key=='internal_chengfeng_burst' or key=='internal_liuguang_stage' or key=='internal_tianbeng_cone'
end
local function validDomain(id,key)
    local s=state(id);local d=s and s.domains[key]
    local _,branch=E.class(id)
    return d and R.tickDuration(d,s.turn) and E.alive(id) and E.allowed(id,branch,false) and d or nil
end
local function activeMark(target,kind,owner)
    local s=state(target);local mark=s and s.marks[kind..':'..owner];local source=state(owner)
    return mark and source and source.turn<mark.expires and mark or nil
end
local function isControlled(status)
    if controls[status] then return true end
    local stat=Ext.Stats.Get(status,nil,false);if not stat then return false end
    local rows=stat.StatusGroups
    if type(rows)=='string' then
        for group in pairs(groups) do if rows:find(group,1,true) then return true end end
    elseif rows then for _,group in pairs(rows) do if groups[group] then return true end end end
    return false
end
local function clearControls(target,source)
    local entity=E.entity(target);if not entity then return false end
    local names={}
    for _,status in pairs(entity.StatusContainer and entity.StatusContainer.Statuses or {}) do
        local name=status.StatusId or status.StatusID;if name and isControlled(name) then names[name]=true end
    end
    for name in pairs(controls) do if E.hasStatus(target,name) then names[name]=true end end
    for name in pairs(names) do E.removeStatus(target,name,source) end
    return next(names)~=nil
end
local function hasControls(id)
    local entity=E.entity(id)
    for _,status in pairs(entity and entity.StatusContainer and entity.StatusContainer.Statuses or {}) do
        if isControlled(status.StatusId or status.StatusID) then return true end
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
    local request=cooperationRequests[id] and cooperationRequests[id][1]
    if Ext.ServerNet then
        Ext.ServerNet.PostMessageToClient(id,'ESC_CooperationState',Ext.Json.Stringify(request and {
            id=id,available=true,token=request.token,options=E.freeOptions(id,request.target)} or {id=id,available=false}))
    end
end
local function requestCooperation(id,owner,target,action)
    local options=E.freeOptions(id,target);if #options==0 then return false end
    sequence=sequence+1
    cooperationRequests[id]=cooperationRequests[id] or {}
    cooperationRequests[id][#cooperationRequests[id]+1]={token=sequence,owner=owner,target=target,action=action,turn=state(owner).turn}
    if #cooperationRequests[id]==1 then sendCooperation(id) end
    return true
end
local function chooseCooperation(id,token,spell,peer)
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
local function spellConditions()
    -- GST strings have a 2048-byte limit. Split the complete boosts, not merely
    -- the conditions: attack + DC repeat each condition in the same string.
    local tests={}
    for spell,key in pairs(keys) do
        local row=spec.spells[key]
        if row and row.base and row.base~='' or key:find('internal_',1,true)==1 then tests[#tests+1]="SpellId('"..spell.."')" end
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
local spellOnly=spellConditions()
local function scopedBoosts(id,prefix,attack,dc)
    for i,condition in ipairs(spellOnly) do
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
local function weaponWisdom(id,s,allowed)
    local wanted={};local cause='ESC_WEAPON_WISDOM_'..id
    for _,off in ipairs({false,true}) do
        local sword=E.sword(id,off);local _,normal=E.swordAttribute(id,off)
        if allowed and sword and E.ability(id,'Wisdom')>normal then wanted[sword]=true end
    end
    for sword in pairs(s.weaponWisdom or {}) do
        if not wanted[sword] and E.entity(sword) then Osi.RemoveBoosts(sword,'WeaponAttackRollAbilityOverride(Wisdom)',0,cause,id) end
    end
    for sword in pairs(wanted) do
        if not (s.weaponWisdom or {})[sword] then Osi.AddBoosts(sword,'WeaponAttackRollAbilityOverride(Wisdom)',cause,id) end
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
local function removeKnownSpell(id,spell,removeChildren)
    if Osi.HasSpell(id,spell)==1 then Osi.RemoveSpell(id,spell,removeChildren) end
end
local function removeKnownPassive(id,passive)
    if Osi.HasPassive(id,passive)==1 then Osi.RemovePassive(id,passive) end
end
local function migrateSkillMenu(id,level,branch)
    -- Only current sword cultivators own this migration. Check each grant on
    -- refresh so old saves, levelling and respec all converge without a save flag.
    if level<=0 then return end
    for _,spell in ipairs(legacyStartingSpells) do removeKnownSpell(id,spell,1) end
    -- The bonus children now belong to their regular technique's container.
    -- Removing an old offhand parent must not remove those retained children.
    for _,spell in ipairs(mergedOffhandContainers) do removeKnownSpell(id,spell,0) end
    removeKnownSpell(id,'Shout_ESC_tianqing_xushi',0)
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
local function refresh(id)
    local level,branch=E.class(id)
    if level==0 and not watched[id] then return end
    local s=syncGuard(id,false);if not s then return end
    if level==0 then
        weaponWisdom(id,s,false)
        for slot in pairs(s.boosts) do if slot~='aura' then E.setBoosts(id,slot,'') end end
        s=state(id);s.frenzy=0;s.shield=0;s.domains={};s.guard=nil;s.chains={};save(id,s)
        for _,status in ipairs({'ESC_MAIN_SWORD','ESC_OFFHAND_SWORD','ESC_ARMOR_BLOCKED','ESC_COUNTER_READY','ESC_COUNTER_RANK2','ESC_COUNTER_RANK3','ESC_EXTRA_ATTACK','ESC_IN_FLIGHT','ESC_CHAIN_LIANCHENG','ESC_CHAIN_WUSHENG'}) do E.removeStatus(id,status,id) end
        return
    end
    migrateSkillMenu(id,level,branch)
    local allowed=E.allowed(id,branch,false);local bonus=R.attackBonus(level,branch)
    for _,entry in ipairs({{'ESC_MAIN_SWORD',E.sword(id)~=nil},{'ESC_OFFHAND_SWORD',E.sword(id,true)~=nil},
        {'ESC_ARMOR_BLOCKED',not allowed and Osi.GetEquippedShield(id)==nil}}) do
        if entry[2] then
            if not E.hasStatus(id,entry[1]) then E.status(id,entry[1],-1,id) end
        else E.removeStatus(id,entry[1],id) end
    end
    local ac=level<3 and 0 or ({taixuan=level>=11 and 6 or 5,tianqing=1,xueyan=1,xingge=0})[branch] or 0
    -- Active guard AC belongs to ESC_COUNTER_READY; never add it twice here.
    if s.dashUntil and s.dashUntil>s.turn then ac=ac+2 end
    E.setBoosts(id,'combat',allowed and 'AC('..ac..')' or '')
    scopedBoosts(id,'sword_stats_',allowed and bonus or 0,allowed and bonus or 0)
    local weaponBoosts={}
    if allowed and E.sword(id) then weaponBoosts[#weaponBoosts+1]='RollBonus(MeleeWeaponAttack,'..bonus..')' end
    if allowed and E.sword(id,true) then weaponBoosts[#weaponBoosts+1]='RollBonus(MeleeOffHandWeaponAttack,'..bonus..')' end
    E.setBoosts(id,'weapon_stats',table.concat(weaponBoosts,';'))
    local extra=R.hitpoints(level,E.ability(id,'Constitution'),branch)-R.hitpoints(level,E.ability(id,'Constitution'),nil)
    E.setBoosts(id,'hp',extra>0 and 'IncreaseMaxHP('..extra..')' or '')
    weaponWisdom(id,s,allowed)
    E.setBoosts(id,'two_swords',allowed and E.sword(id) and E.sword(id,true) and 'TwoWeaponFighting()' or '')
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
    local off=meta and meta.hand=='off' or not E.sword(id) and E.sword(id,true)~=nil
    if spell and off and Ext.Stats.Get(spell..'_Off',nil,false) then spell=spell..'_Off' end
    if not spell or not Ext.Stats.Get(spell,nil,false) then E.log('Missing native helper '..tostring(key));return false end
    pendingHelpers[id]=pendingHelpers[id] or {}
    pendingHelpers[id][#pendingHelpers[id]+1]={key=key,target=target,meta=meta or {}}
    E.useSpell(id,spell,target);return true
end
local function cooperation(id,target)
    if E.friend(id,target) then E.restore(id,R.cooperation(E.class(id)));return true end
    return false
end
local function recipients(owner,range,includeSelf)
    return E.nearby(owner,range,function(a,b) return includeSelf and a==b or E.friend(a,b) end)
end
local function updateAuras()
    for id in pairs(watched) do
        if not E.entity(id) then watched[id]=nil;auraTargets[id]=nil;rescueRequests[id]=nil end
    end
    local rows={}
    for owner in pairs(watched) do
        local level,branch=E.class(owner)
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
            for _,target in ipairs(recipients(owner,6,true)) do
                if validDomain(owner,'taixuan_taiqing') then rows[target]=rows[target] or {};rows[target].domain=true end
                if validDomain(owner,'xingge_zhangjian') then rows[target]=rows[target] or {};rows[target].team=true end
            end
            if validDomain(owner,'taixuan_taiqing') then
                for _,target in ipairs(E.nearby(owner,6,E.enemy)) do rows[target]=rows[target] or {};rows[target].hostileDomain=true end
            end
        end
    end
    for id in pairs(watched) do
        local s=state(id);local dr=0
        for target in pairs(s.kills) do if E.entity(target) and E.alive(target) then s.kills[target]=nil end end
        for key,p in pairs(s.protections) do
            local owner=state(p.owner)
            if not owner or not E.alive(p.owner) or (p.kind=='huifeng' and not E.hasStatus(id,'ESC_XINGGE_PROTECTION'))
                or owner.turn>=p.expires then
                s.protections[key]=nil
                if p.kind=='chengfeng' then E.setBoosts(id,'chengfeng','') end
            else dr=math.max(dr,p.reduction) end
        end
        if dr>0 then rows[id]=rows[id] or {};rows[id].protectionDR=dr end
        for key,debuff in pairs(s.debuffs) do
            local owner=state(debuff.owner)
            if not owner or owner.turn>=debuff.expires then s.debuffs[key]=nil
            else
                rows[id]=rows[id] or {};local row=rows[id]
                row.breakAC=math.max(row.breakAC or 0,math.abs(debuff.ac or 0))
                row.attackDown=math.max(row.attackDown or 0,math.abs(debuff.attack or 0))
                row.slow=row.slow or debuff.slow
            end
        end
        save(id,s)
    end
    for target in pairs(auraTargets) do if not rows[target] then E.setBoosts(target,'aura','') end end
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
local function startDomain(id,key)
    local s=state(id);s.domains[key]=R.applyDuration(s.domains[key],s.turn,4)
    sequence=sequence+1;s.domains[key].sequence=sequence;save(id,s)
    local statuses={taixuan_taiqing='ESC_SWORD_DOMAIN',xueyan_xuehai='ESC_BLOOD_ROBE',
        tianqing_tianjian='ESC_TIANQING_AFTERSHOCK',xingge_fengyu='ESC_DAMAGE_SHARE',xingge_zhangjian='ESC_TEAM_RESONANCE'}
    E.status(id,statuses[key],4,id);updateAuras()
end
local function pulse(id,key)
    if not validDomain(id,key) then return end
    local s=state(id)
    for _,target in ipairs(E.nearby(id,6,E.enemy)) do
        helper(id,key=='taixuan_taiqing' and 'internal_taiqing_pulse' or 'internal_blood_pulse',target)
        if key=='taixuan_taiqing' and s.focus==target then helper(id,'internal_taiqing_pulse',target);helper(id,'internal_taiqing_pulse',target) end
    end
end
local function copyPosition(point) return point and {point[1],point[2],point[3]} or nil end
local function beginCast(id,spell,action,target,position)
    local name=E.spellName(spell);local key=keyFor(name);local c=casts[action]
    if c and c.id==id then
        c.target=target or c.target;c.position=position and copyPosition(position) or c.position
        if target and not c.targetPosition then c.targetPosition=copyPosition(E.position(target)) end
        return c
    end
    if E.class(id)>0 then refresh(id);scopedBoosts(id,'cast_snapshot_',0,0);E.setBoosts(id,'cast_weapon_accuracy','') end
    c={id=id,key=key,spell=name,target=target,position=copyPosition(position),action=action,targets={},rewards={},firstHits={},
        alias=aliases[name] or {},startPosition=copyPosition(E.position(id)),targetPosition=target and copyPosition(E.position(target))}
    local queue=pendingHelpers[id]
    if queue and queue[1] and queue[1].key==key then c.meta=table.remove(queue,1).meta end
    c.meta=c.meta or {};c.level,c.branch=E.class(id)
    local original=c.meta.originalSpell or name
    c.basicSword=(original=='Target_MainHandAttack' and E.sword(id)~=nil)
        or ((original=='Target_OffhandAttack' or original=='Target_OffHandAttack') and E.sword(id,true)~=nil)
    local sourceState=c.level>0 and state(id) or nil;local aura=auraTargets[id] or {}
    c.damageOptions={domain=aura.domain,team=aura.team,charge=sourceState and sourceState.chargeUntil and sourceState.chargeUntil>sourceState.turn,
        descent=c.level>0 and validDomain(id,'tianqing_tianjian')~=nil}
    local row=spec.spells[c.alias.parent or key]
    if row and sourceState and (row.base=='W' or row.base=='WQ') and not (row.base=='WQ' and sourceState.qiSword) then
        local modifier=E.swordAttribute(id,c.alias.hand=='off' or c.alias.offhand)
        local adjustment=modifier-E.ability(id,'Wisdom')
        E.setBoosts(id,'cast_weapon_accuracy',adjustment>0 and "IF(SpellId('"..name.."')):RollBonus(Attack,"..adjustment..')' or '')
    end
    local resource=E.resourceEntry(id,spec.opportunityResource)
    c.usedOpportunity=resource and resource.Amount>0 and E.hasStatus(id,'ESC_EXTRA_ATTACK') or false
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
local function failedCast(id,spell,action)
    local c=casts[action]
    if c then c.failed=true end
    if E.class(id)>0 then scopedBoosts(id,'cast_snapshot_',0,0);E.setBoosts(id,'cast_weapon_accuracy','') end
    trace('CastSpellFailed',{source=id,spell=spell,action=action})
end
local function castEffect(c)
    local id,key,target=c.id,c.key,c.target or c.id;local level,branch=E.class(id)
    if not key or level==0 or c.invalid then return end
    local s=state(id)
    if key=='tiaoxi' or key=='tianqing_xushi' then E.restore(id,R.breath(level,key=='tianqing_xushi' and 'tianqing' or branch,true,E.combat(id)))
    elseif key=='taixuan_guiyuan' or key=='tianqing_nixi' or key=='xueyan_huichao' or key=='xingge_xiangfu' then
        if target==id or key=='xingge_xiangfu' and E.friend(id,target) and E.distance(id,target)<=18 then
            local actual=E.heal(target,E.maxHp(target)*R.healing(level,branch));if actual>0 then cooperation(id,target) end
        end
    elseif key=='qi_sword' then
        s.qiSword=not s.qiSword;save(id,s)
        if s.qiSword then E.status(id,'ESC_QI_MODE',-1,id) else E.removeStatus(id,'ESC_QI_MODE',id) end
    elseif key=='xueyan_damage_mode' then
        s.damageMode=s.damageMode=='Necrotic' and 'Force' or 'Necrotic';save(id,s)
        if s.damageMode=='Force' then E.status(id,'ESC_FORCE_MODE',-1,id) else E.removeStatus(id,'ESC_FORCE_MODE',id) end
    elseif key=='xueyan_ranxue' then
        local hp,frenzy=R.bloodCost(E.hp(id),E.maxHp(id),s.frenzy);if hp then Osi.SetHitpoints(id,hp,'Guaranteed');setFrenzy(id,frenzy) end
    elseif key=='control_release' or key=='xingge_fuchen' then
        if target==id or E.friend(id,target) and E.distance(id,target)<=18 then
            local removed=clearControls(target,id);E.status(target,'ESC_CONTROL_RESISTANCE',2,id);if removed then cooperation(id,target) end
        end
    elseif key=='focus_target' then s.focus=target;save(id,s)
    elseif key=='taixuan_liuguang' then
        if c.target and E.entity(target) and E.enemy(id,target) then
            for _=1,3 do helper(id,'internal_liuguang_stage',target,{parentAction=c.action}) end
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
                    if enemy~=target and planar>0 and x*x+y*y+z*z<=144+1e-9
                        and (x*dx+z*dz)/(planar*direction)>=math.sqrt(.5)-1e-9 and E.visible(id,enemy) then
                        helper(id,'internal_tianbeng_cone',enemy,{parentAction=c.action,hand=c.alias.hand})
                    end
                end
            end
        end
    elseif key=='xingge_huifeng' then
        if target==id or E.friend(id,target) and E.distance(id,target)<=18 then
            local t=state(target);t.protections['huifeng:'..id]={owner=id,kind='huifeng',expires=s.turn+2,reduction=.20};save(target,t)
            cooperation(id,target);updateAuras()
            for _,enemy in ipairs(E.nearby(target,3,function(_,other) return E.enemy(id,other) end)) do helper(id,'internal_huifeng_control',enemy,{parentAction=c.action}) end
        end
    elseif key=='tianqing_tianfeng' then s.chargeUntil=s.turn+2;save(id,s)
    elseif key=='taixuan_taiqing' or key=='xueyan_xuehai' then startDomain(id,key);pulse(id,key)
    elseif key=='tianqing_tianjian' or key=='xingge_fengyu' or key=='xingge_zhangjian' then
        if key~='tianqing_tianjian' or c.alias.impact then startDomain(id,key) end
        if key=='xingge_fengyu' then for _,ally in ipairs(recipients(id,6,false)) do cooperation(id,ally) end end
    elseif key=='xingge_chengfeng' then
        if target==id or E.friend(id,target) then
            E.setBoosts(target,'chengfeng','IgnoreLeaveAttackRange();ActionResource(Movement,6,0)')
            local t=state(target);t.protections['chengfeng:'..id]={owner=id,kind='chengfeng',expires=s.turn+1,reduction=0};save(target,t);cooperation(id,target)
            for _,enemy in ipairs(E.nearby(target,3,function(_,other) return E.enemy(id,other) end)) do helper(id,'internal_chengfeng_burst',enemy,{parentAction=c.action,hand=c.alias.hand}) end
        end
    elseif key=='xingge_tongzhou' then
        for _,ally in ipairs(recipients(id,6,false)) do
            requestCooperation(ally,id,target,c.action)
        end
    elseif key=='recall_sword' then
        local entity=E.entity(target)
        if target~=id and entity and Osi.IsItem(target)==1 and E.distance(id,target)<=18 and E.visible(id,target)
            and Osi.GetOwner(target)==id and Osi.IsEquipped(target)==0 then Osi.Equip(id,target,1,1,0) end
    elseif key=='sword_flight' then
        if #E.nearby(id,3,E.enemy)==0 and E.allowed(id,branch,true) then
            E.setResource(id,spec.flightResource,24);E.status(id,'ESC_IN_FLIGHT',1,id)
        end
    elseif key=='internal_flight_move' then
        local pool=E.resourceEntry(id,spec.flightResource)
        if pool and pool.Amount<=0 then E.removeStatus(id,'ESC_IN_FLIGHT',id) end
    elseif key=='internal_chain_move' then
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
    local aura=auraTargets[target]
    if aura then factor=factor*(1-(aura.sideReduction or 0))*(1-(aura.protectionDR or 0)) end
    return factor
end
local function transferDamage(target,amount,parts,source)
    if amount<=0 then return end
    local context={target=target,source=source,transfer=true,eligible=false,total=0,emitted=0,factor=reductionFactor(target)}
    local previous=pendingTransfer;pendingTransfer=context
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
    pendingTransfer=previous
end
local function defense(target,damage,bypass,transfer,parts,stage)
    local level,branch=E.class(target);local s=state(target);if not s then return damage,damage end
    if not bypass then
        local other={}
        if E.allowed(target,branch,false) then
            if s.guard and E.hasStatus(target,'ESC_COUNTER_READY') then other[#other+1]=s.guard.reduction end
            if validDomain(target,'tianqing_tianjian') then other[#other+1]=.25 end
            if validDomain(target,'xingge_fengyu') then other[#other+1]=.30 end
            -- Keep floating value until the final stage/target rounding, including aura DR.
            damage=damage*(1-R.baseReduction(level,branch,s.frenzy))
            for _,dr in ipairs(other) do damage=damage*(1-dr) end
        end
        local aura=auraTargets[target]
        if aura then damage=damage*(1-(aura.sideReduction or 0))*(1-(aura.protectionDR or 0)) end
    end
    if stage then
        stage.defenseFloat=stage.defenseFloat+math.max(0,damage)
        local cumulative=math.floor(stage.defenseFloat+1e-9)
        damage=cumulative-stage.defenseEmitted;stage.defenseEmitted=cumulative
    else damage=math.floor(math.max(0,damage)+1e-9) end
    local credited=damage;damage,s.shield=R.shieldAbsorb(damage,s.shield);save(target,s)
    if not transfer then
        local protectors={}
        for owner in pairs(watched) do
            local domain=validDomain(owner,'xingge_fengyu')
            if domain and E.friend(owner,target) and E.distance(owner,target)<=6 then
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
    local s=state(context.source);if not s or (not context.eligible and not context.direct) then return 1 end
    local own=context.eligible
    local c=casts[context.action];local row=context.key and spec.spells[context.key];local snapshot=c and c.snapshot
    if c and c.alias.parent then row=spec.spells[c.alias.parent] end
    local aura=auraTargets[context.source] or {};local followup=false
    local options=c and c.damageOptions or {domain=aura.domain,team=aura.team,
        charge=s.chargeUntil and s.chargeUntil>s.turn,descent=validDomain(context.source,'tianqing_tianjian')~=nil}
    for owner in pairs(watched) do if E.friend(owner,context.source) and activeMark(context.target,'followup',owner) then followup=true;break end end
    return R.damageMultiplier({level=context.level,held=own and context.branch=='xueyan' and (snapshot and snapshot.held or s.frenzy) or 0,
        spent=own and snapshot and snapshot.spent or 0,weakpoint=own and activeMark(context.target,'weakpoint',context.source)~=nil,
        domain=options.domain,team=options.team,followup=followup,
        charge=own and options.charge,descent=own and options.descent,
        regular=own and row and row.level>=6 and row.level<=9 and row.cost==10})
end
local function stageKey(source,action,target) return (source or '_environment_')..':'..tostring(action)..':'..target end
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
    if stage then
        stage.outgoingFloat=stage.outgoingFloat+outgoing
        local cumulative=math.floor(stage.outgoingFloat+1e-9)
        outgoing=cumulative-stage.outgoingEmitted;stage.outgoingEmitted=cumulative
    end
    if context.key=='taixuan_yixiantian' then
        local c=casts[context.action]
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
            if E.forceImmune(context.target) then outgoing=0
            else
                local raw=hit.Damage and hit.Damage.TotalDamage or total
                -- Native definition uses one combined damage functor for this line.
                c.lineDamage=c.lineDamage or raw*multiplier(context)
                outgoing=c.lineDamage*(.5^(c.lineOrder[context.target] or 0))
            end
        end
    end
    -- TQ ultimate ally/neutral quarter damage is defined natively before saves;
    -- multiplying it here again would incorrectly reduce it to one sixteenth.
    local final,credited=defense(context.target,outgoing,context.key=='taixuan_yixiantian',context.transfer,hit.DamageList,stage)
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
        c.targets[context.target]=true
        if context.direct then c.directDamage=true end
    end
    if not context.key and not context.eligible then flushStage(context.source,context.action,context.target) end
end
local function mark(target,kind,owner)
    local s=state(target);local source=state(owner);if not s or not source then return end
    s.marks[kind..':'..owner]=kind=='followup' and R.recastFollowup(source.turn) or {expires=source.turn+3,used={}}
    save(target,s);E.status(target,kind=='followup' and 'ESC_FOLLOWUP' or 'ESC_WEAKPOINT',3,owner)
    if kind=='weakpoint' then
        local condition="IF(HasStatus('ESC_WEAKPOINT',context.Target,context.Source))"
        local boosts={condition..':RollBonus(Attack,2)'}
        for _,damageType in ipairs({'Slashing','Piercing','Bludgeoning','Acid','Cold','Fire','Force','Lightning','Necrotic','Poison','Psychic','Radiant','Thunder'}) do
            boosts[#boosts+1]=condition..':IgnoreResistance('..damageType..',Resistant)'
        end
        E.setBoosts(owner,'weakpoint',table.concat(boosts,';'))
    else
        for _,ally in ipairs(recipients(owner,1000,false)) do
            E.setBoosts(ally,'followup_'..owner,"IF(HasStatus('ESC_FOLLOWUP',context.Target,'"..owner.."')):RollBonus(Attack,2)")
        end
    end
end
local function resonance(c,target)
    if c.key=='internal_resonance' or c.meta.resonance then return end
    for owner in pairs(watched) do
        local domain=validDomain(owner,'xingge_zhangjian')
        if domain and (c.id==owner or E.friend(owner,c.id)) and E.distance(owner,c.id)<=6
            and E.allowed(owner,'xingge',true) and not domain.used[c.id] then
            domain.used[c.id]=true;local s=state(owner);s.domains.xingge_zhangjian=domain;save(owner,s)
            local victims={target}
            for other in pairs(c.targets) do if other~=target and E.enemy(owner,other) and E.distance(target,other)<=3 then victims[#victims+1]=other end end
            for _,victim in ipairs(victims) do helper(owner,'internal_resonance',victim,{resonance=true,rewardToken=tostring(c.action)..':'..c.id}) end
        end
    end
end
local function hit(source,target,action)
    flushStage(source,action,target)
    local c=casts[action];if not c then return end
    c.targets[target]=true
    if not c.firstHits[target] then
        c.firstHits[target]=true
        if c.key=='taixuan_zhaoxi' then mark(target,'weakpoint',source) elseif c.key=='xingge_wenlu' then mark(target,'followup',source) end
    end
    local rewards={}
    for owner in pairs(watched) do
        local followup=E.friend(owner,source) and activeMark(target,'followup',owner)
        if followup and R.followup(followup,source) then local s=state(target);s.marks['followup:'..owner]=followup;save(target,s);rewards[owner]=true end
    end
    if c.meta.cooperator then rewards[c.meta.cooperator]=true end
    for owner in pairs(rewards) do if not c.rewards[owner] then E.restore(owner,R.cooperation(E.class(owner)));c.rewards[owner]=true end end
    if c.key=='internal_resonance' then
        local s=state(source);s.resonanceRewards=s.resonanceRewards or {}
        if R.once(s.resonanceRewards,c.meta.rewardToken or tostring(action)) then E.restore(source,R.cooperation(E.class(source))) end
        save(source,s)
    elseif not c.resonanceScheduled then
        c.resonanceScheduled=true
        Ext.Timer.WaitFor(1,function() resonance(c,c.target and c.targets[c.target] and c.target or target) end)
    end
end
local function controlFailed(target,marker,source,action)
    local c=casts[action];if not c then return false end
    local row=spec.spells[c.alias.parent or c.key]
    if c.meta.parentAction and casts[c.meta.parentAction] then c=casts[c.meta.parentAction] end
    local control=row and row.hitControl
    if not control or control.marker~=marker or not E.enemy(source,target) then return false end
    c.controlApplied=c.controlApplied or {}
    if c.key=='tianqing_tiandi' and c.controlApplied[target] then return false end
    c.controlApplied[target]=true
    local s,owner=state(target),state(source)
    s.debuffs[source..':'..c.key]={owner=source,expires=owner.turn+(control.duration or 1),
        ac=(not control.mainOnly or c.target==target) and control.ac or nil,attack=control.attack,slow=control.slow}
    save(target,s)
    if control.prone then E.status(target,'PRONE',1,source) end
    updateAuras();return true
end
local function finishCast(id,spell,action)
    local c=casts[action] or beginCast(id,spell,action,id)
    if c.finished or c.failed then return end;c.finished=true;castEffect(c)
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
    local row=c.key and spec.spells[c.key]
    if row and row.action=='sword' and not row.internal and not c.alias.internal and not c.alias.continuation and not c.alias.bonusOnly and spec.opportunityResource then
        local pool=E.resourceEntry(id,spec.opportunityResource)
        if pool then
            if not c.usedOpportunity then pool.Amount=R.opportunities(c.level,c.branch)-1;pool.MaxAmount=math.max(pool.MaxAmount,pool.Amount);E.entity(id):Replicate('ActionResources') end
            if pool.Amount>0 then E.status(id,'ESC_EXTRA_ATTACK',-1,id) else E.removeStatus(id,'ESC_EXTRA_ATTACK',id) end
        end
    end
    -- Projectile callbacks can be later than CastedSpell. Do not discard their snapshot.
    Ext.Timer.WaitFor(30000,function() if casts[action]==c then casts[action]=nil end end)
end
local function turnStarted(id)
    for ally,queue in pairs(cooperationRequests) do
        for i=#queue,1,-1 do if queue[i].owner==id then table.remove(queue,i) end end
        sendCooperation(ally)
    end
    for owner in pairs(watched) do
        if validDomain(owner,'tianqing_tianjian') and E.enemy(owner,id) and E.distance(owner,id)<=6 then helper(owner,'internal_aftershock',id) end
    end
    local s=state(id);if not s then return end
    s.turn=s.turn+1;s.autoReleased=false;s.resonanceRewards={}
    for key,domain in pairs(s.domains) do if not R.tickDuration(domain,s.turn) then s.domains[key]=nil else domain.used={} end end
    -- Native StatusRemoved ends guard, including real-time expiry outside combat.
    if s.shieldUntil and s.shieldUntil<=s.turn then s.shield=0 end
    save(id,s)
    if spec.opportunityResource then local pool=E.resourceEntry(id,spec.opportunityResource);if pool then pool.Amount=0;E.entity(id):Replicate('ActionResources') end end
    E.removeStatus(id,'ESC_EXTRA_ATTACK',id)
    E.setResource(id,spec.chainMoveResource,0);E.setResource(id,spec.flightResource,0)
    E.removeStatus(id,'ESC_CHAIN_LIANCHENG',id);E.removeStatus(id,'ESC_CHAIN_WUSHENG',id);E.removeStatus(id,'ESC_IN_FLIGHT',id)
    s=state(id);s.chains={};save(id,s)
    local level,branch=E.class(id)
    if level>0 and branch=='taixuan' and E.allowed(id,branch,false) then E.restore(id,R.breath(level,branch,false,true));E.heal(id,E.maxHp(id)*(level>=11 and .06 or .05),true) end
    updateAuras();refresh(id);updateRescue(id)
    if validDomain(id,'taixuan_taiqing') then pulse(id,'taixuan_taiqing') end
    if validDomain(id,'xueyan_xuehai') then pulse(id,'xueyan_xuehai') end
end
local function killed(target,source,action)
    local level,branch=E.class(source);local c=casts[action]
    if branch~='xueyan' or not c or not E.allowed(source,branch,false) or not (offensiveKey(c.key) or c.swordDamage) or not E.enemy(source,target) then return end
    local s=state(source)
    if R.once(s.kills,target) then save(source,s);local heal,yuan,frenzy=R.killReward(level,E.maxHp(source));E.heal(source,heal);E.restore(source,yuan);addFrenzy(source,frenzy) end
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
    rescueRequests={};cooperationRequests={};pendingAvatarRefreshes={}
    timerGeneration=timerGeneration+1;local generation=timerGeneration
    refreshClassActors(true)
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
    local c=casts[evt.StoryActionId];if c and eligible then c.swordDamage=true end
    trace('DealDamage',{source=source,target=target,spell=spell,action=evt.StoryActionId,hp=E.hp(target),temporaryHp=E.tempHp(target),eligible=eligible})
    contexts[#contexts+1]={source=source,target=target,key=key,spell=spell,level=level,branch=branch,action=evt.StoryActionId,
        hp=E.hp(target),eligible=eligible,transfer=transferred,direct=spell~=nil and (status==nil or status=='')}
end)
Ext.Events.BeforeDealDamage:Subscribe(function(evt)
    if not pendingTransfer and #contexts==0 then trace('UnpairedBeforeDealDamage',{}) end
    beforeDamage(evt)
end)
Ext.Events.DealtDamage:Subscribe(function(evt) afterDamage(evt);contexts[#contexts]=nil end)
local functorRecipientField={AttackTarget='Target',NearbyAttacked='Target',NearbyAttacking='Target',
    Equip='Target',Move='Target',Target='Source',Source='Source',
    [1]='Target',[3]='Target',[4]='Source',[5]='Target',[6]='Target',[7]='Target',[8]='Source'}
local function functorRecipient(params)
    if not params then return nil end
    -- Params is a tagged variant. Missing proxy properties throw in BG3SE, so
    -- only read fields declared for this concrete FunctorContextType.
    local field=functorRecipientField[params.Type]
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
Ext.Events.ExecuteFunctor:Subscribe(function(evt)
    local context={}
    local params=evt.Params
    local target=functorRecipient(params)
    for _,functor in pairs(evt.Functor and evt.Functor.FunctorList or {}) do
        if tostring(functor.TypeId)=='RegainHitPoints' and not tostring(functor.HealingType):find('Regeneration',1,true) then context.healing=true end
    end
    if context.healing and target then context.target=target;context.before=E.hp(target) end
    healingContexts[#healingContexts+1]=context
end)
Ext.Events.AfterExecuteFunctor:Subscribe(function(evt)
    local context=healingContexts[#healingContexts];healingContexts[#healingContexts]=nil
    if not context or not context.target then return end
    local gained=E.hp(context.target)-context.before
    local mult=Runtime.HealingMultiplier(context.target)
    if gained>0 and mult>1 then E.heal(context.target,gained*(mult-1),true) end
end)
Ext.Osiris.RegisterListener('UsingSpell',5,'before',function(id,spell,kind,element,action) beginCast(id,spell,action) end)
Ext.Osiris.RegisterListener('UsingSpellOnTarget',6,'before',function(id,target,spell,kind,element,action) beginCast(id,spell,action,target) end)
Ext.Osiris.RegisterListener('UsingSpellAtPosition',8,'before',function(id,x,y,z,spell,kind,element,action) beginCast(id,spell,action,nil,{x,y,z}) end)
Ext.Osiris.RegisterListener('CastedSpell',5,'after',function(id,spell,kind,element,action) finishCast(id,spell,action) end)
Ext.Osiris.RegisterListener('CastSpellFailed',5,'after',function(id,spell,kind,element,action) failedCast(id,spell,action) end)
Ext.Osiris.RegisterListener('StatusApplied',4,'after',function(id,status,source,action)
    trace('StatusApplied',{target=id,status=status,source=source,action=action})
    if Osi.IsItem(id)==1 then local owner=Osi.GetOwner(id);if owner and E.class(owner)>0 then refresh(owner) end end
    if status=='ESC_COUNTER_READY' then syncGuard(id,true);refresh(id)
    elseif status=='ESC_HIT_MARKER' then hit(source,id,action)
    elseif status=='ESC_TIANDI_TARGET' then
        local c=casts[action]
        if c then
            c.tiandiTargets=c.tiandiTargets or {}
            if not c.tiandiTargets[id] then
                c.tiandiTargets[id]=true
                helper(source,'internal_tiandi_stage',id,{parentAction=action,hand=c.alias.hand})
                helper(source,'internal_tiandi_stage',id,{parentAction=action,hand=c.alias.hand})
            end
        end
    elseif status:find('ESC_SAVEFAIL_',1,true)==1 then controlFailed(id,status,source,action)
    elseif status=='DOWNED' or status=='DYING' or status=='DEAD' then local s=state(id);if s then s.shield=0;s.domains={};save(id,s);setFrenzy(id,0);updateAuras() end end
    if E.class(id)>0 then
        if status=='ESC_CONTROL_RESISTANCE' then refresh(id) end
        updateRescue(id)
    end
end)
Ext.Osiris.RegisterListener('StatusRemoved',4,'after',function(id,status,source,action)
    if status=='ESC_COUNTER_READY' and not E.hasStatus(id,status) then
        local s=state(id);if s then s.guard=nil;save(id,s) end
        -- Leave rank markers on their native clock: an old Ready removal
        -- can be delivered after a new rank is applied during refresh.
        if E.class(id)>0 then refresh(id) end
    elseif status=='ESC_XINGGE_PROTECTION' then
        local s=state(id)
        if s then
            for key,p in pairs(s.protections) do
                if p.kind=='huifeng' and (not E.hasStatus(id,status) or p.owner==source) then s.protections[key]=nil end
            end
            save(id,s);updateAuras()
        end
    end
    if Osi.IsItem(id)==1 then local owner=Osi.GetOwner(id);if owner and E.class(owner)>0 then refresh(owner) end end
    if status=='ESC_CONTROL_RESISTANCE' and E.class(id)>0 then refresh(id) end
end)
Ext.Osiris.RegisterListener('StatusAttempt',4,'before',statusAttempt)
Ext.Osiris.RegisterListener('KilledBy',4,'after',function(target,owner,attacker,action) killed(target,owner,action) end)
Ext.Osiris.RegisterListener('AttackedBy',7,'after',function(target,owner,attacker,damageType,amount,cause,action)
    local c=casts[action]
    if c and not c.key and c.directDamage then hit(owner,target,action) end
end)
Ext.Osiris.RegisterListener('TurnStarted',1,'after',turnStarted)
Ext.Osiris.RegisterListener('LeveledUp',1,'after',refresh)
Ext.Osiris.RegisterListener('RespecCompleted',1,'after',refresh)
Ext.Osiris.RegisterListener('Equipped',2,'after',function(item,id) refresh(id);updateAuras() end)
Ext.Osiris.RegisterListener('Unequipped',2,'after',function(item,id) refresh(id);updateAuras() end)
-- New-game character creation can finish after SessionLoaded and its initial
-- equipment events. Discover the finalized actors when gameplay is ready.
Ext.Osiris.RegisterListener('LevelGameplayReady',2,'after',function() refreshClassActors(false) end)
Ext.Osiris.RegisterListener('UserAvatarCreated',3,'after',function(user,avatar,guardian) refreshNewAvatar(avatar) end)
Ext.Events.SessionLoaded:Subscribe(sessionLoaded)
Ext.Events.NetMessage:Subscribe(function(evt)
    if evt.Channel~='ESC_ControlRescueIntent' and evt.Channel~='ESC_CooperationIntent' then return end
    local ok,data=pcall(Ext.Json.Parse,evt.Payload);if not ok then return end
    if type(data)=='table' and type(data.id)=='string' and type(data.token)=='number' then
        if evt.Channel=='ESC_ControlRescueIntent' then rescue(data.id,data.token,evt.UserID)
        elseif type(data.spell)=='string' then chooseCooperation(data.id,data.token,data.spell,evt.UserID) end
    end
end)
Runtime.Refresh,Runtime.State,Runtime.BeginCast,Runtime.FinishCast=refresh,state,beginCast,finishCast
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
ESC.Runtime,ESC.Refresh,ESC.State=Runtime,refresh,state
