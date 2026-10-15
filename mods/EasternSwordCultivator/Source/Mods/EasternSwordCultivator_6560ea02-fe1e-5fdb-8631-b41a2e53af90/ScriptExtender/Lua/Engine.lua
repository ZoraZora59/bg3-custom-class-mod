-- Engine boundary: BG3SE v30+ entity fields and installed Patch 8 Osiris signatures.
local E = {}
local R = ESC.Rules
E.resource = 'ff9884b7-6054-595d-8ff5-2d39bbb41dd2'
E.action = '734cbcfb-8922-4b6d-8330-b2a7e4c14b6a'
E.reaction = '45ff0f48-b210-4024-972f-b64a44dc6985'
E.classes = {}

function E.entity(id) return id and Ext.Entity.Get(id) or nil end
function E.uuid(entity)
    if not entity then return nil end
    return entity.Uuid and tostring(entity.Uuid.EntityUuid) or nil
end
function E.sameEntity(first,second)
    if first==nil or second==nil then return false end
    if first==second then return true end
    -- Osiris may supply Name_GUID while ECS causes expose GUID or handles.
    -- Resolve both through the documented Entity API rather than compare text.
    local firstUuid,secondUuid=E.uuid(E.entity(first)),E.uuid(E.entity(second))
    return firstUuid~=nil and secondUuid~=nil and firstUuid:lower()==secondUuid:lower()
end
function E.refUuid(ref)
    if not ref then return nil end
    local ok,entity=pcall(function() return E.entity(ref.Handle or ref) end)
    return ok and E.uuid(entity) or nil
end
function E.position(id)
    local entity=E.entity(id)
    if entity and entity.Transform then return entity.Transform.Transform.Translate end
end
function E.class(id)
    local entity=E.entity(id)
    if entity and entity.Classes then
        for _, info in ipairs(entity.Classes.Classes) do
            if tostring(info.ClassUUID)==E.classes.common then
                local branch
                for key, uuid in pairs(E.classes) do
                    if key~='common' and tostring(info.SubClassUUID)==uuid then branch=key end
                end
                return info.Level,branch
            end
        end
    end
    return 0,nil
end
function E.resourceEntry(id, uuid)
    if not uuid then return nil end
    local entity=E.entity(id)
    local resources=entity and entity.ActionResources
    local rows=resources and resources.Resources[uuid]
    if rows then
        for _, row in ipairs(rows) do if row.Level==0 then return row end end
    end
end
function E.restore(id,amount)
    local row=E.resourceEntry(id,E.resource)
    if not row then return 0 end
    local value,delta=R.recover(row.Amount,row.MaxAmount,amount)
    row.Amount=value
    E.entity(id):Replicate('ActionResources')
    return delta
end
function E.spendResource(id,uuid,amount)
    local row=E.resourceEntry(id,uuid)
    if not row or row.Amount<amount then return false end
    row.Amount=row.Amount-amount
    E.entity(id):Replicate('ActionResources')
    return true
end
function E.maxHp(id) return id and Osi.GetMaxHitpoints(id) or 0 end
function E.hp(id) return id and Osi.GetHitpoints(id) or 0 end
function E.heal(id,amount,regeneration)
    if ESC.Runtime and ESC.Runtime.NotifyHealingInterference then ESC.Runtime.NotifyHealingInterference(id) end
    local before=E.hp(id)
    if before<=0 then return 0 end
    if not regeneration and ESC.Runtime and ESC.Runtime.HealingMultiplier then
        amount=amount*ESC.Runtime.HealingMultiplier(id)
    end
    Osi.SetHitpoints(id,math.min(E.maxHp(id),before+math.ceil(amount)),'Guaranteed')
    return E.hp(id)-before
end
function E.status(id,name,rounds,source)
    Osi.ApplyStatus(id,name,rounds<0 and -1 or rounds*6,1,source or id)
end
function E.hasStatus(id,name) return Osi.HasActiveStatus(id,name)==1 end
function E.removeStatus(id,name,source) Osi.RemoveStatus(id,name,source or id) end
function E.alive(id) return Osi.IsDead(id)==0 and not E.hasStatus(id,'DOWNED') end
function E.combat(id) return Osi.IsInCombat(id)==1 end
function E.character(id) return id~=nil and Osi.IsCharacter(id)==1 end
function E.friend(a,b)
    return a~=b and E.character(a) and E.character(b) and Osi.IsInPartyWith(a,b)==1 and Osi.IsSummon(b)==0
end
function E.enemy(a,b) return a~=b and E.character(a) and E.character(b) and Osi.IsEnemy(a,b)==1 end
function E.nearby(id,range,relation)
    local result={}
    local center=E.position(id)
    if not center then return result end
    for _, entity in ipairs(Ext.Entity.GetAllEntitiesWithComponent('Health')) do
        local target=E.uuid(entity)
        local position=target and E.position(target)
        if position and Osi.IsCharacter(target)==1 and E.alive(target) and R.within(position,center,range)
            and Osi.IsOnStage(target)==1 and (not relation or relation(id,target)) then result[#result+1]=target end
    end
    return result
end
function E.ability(id,ability) return R.modifier(Osi.GetAbility(id,ability) or 10) end
local submittedBoosts={}
local function submittedBoost(id,slot,boost)
    local owner=E.uuid(E.entity(id)) or id
    submittedBoosts[owner]=submittedBoosts[owner] or {}
    -- Osiris queues native boost creation. Do not submit the same slot again
    -- while a load reconciliation still sees the pre-add native container.
    -- This is evidence of an actual request in this Lua session, not saved
    -- state. The SE reload resets it; no assumed native queue delay is needed.
    submittedBoosts[owner][slot]=boost
end
function E.setBoosts(id,slot,boost)
    assert(not boost or #boost<=2048,'ESC boost exceeds the native GST 2048-byte bound: '..slot)
    local entity=E.entity(id)
    if not entity then return end
    local state=entity.Vars.ESC_State or {}
    state.boosts=state.boosts or {}
    local old=state.boosts[slot]
    if (old or '')==(boost or '') then return end
    if old and old~='' then Osi.RemoveBoosts(id,old,0,'ESC_'..slot,id) end
    if boost and boost~='' then submittedBoost(id,slot,boost);Osi.AddBoosts(id,boost,'ESC_'..slot,id) end
    state.boosts[slot]=boost
    entity.Vars.ESC_State=state
    if ESC.Runtime and ESC.Runtime.TrackState then ESC.Runtime.TrackState(id,state) end
end
local function boostDescriptionKey(name,params)
    -- The owned boost vocabulary has no significant whitespace in arguments.
    return tostring(name)..'('..tostring(params or ''):gsub('%s+','')..')'
end
local function boostStatements(boost)
    local statements={}
    for text in boost:gmatch('[^;]+') do
        local body=text:match('^%s*IF%b():%s*(.*)$') or text
        local name,params=body:match('^%s*([%w_]+)%((.*)%)%s*$')
        if not name then return nil end
        statements[#statements+1]={text=text,key=boostDescriptionKey(name,params)}
    end
    return statements
end
function E.restoreBoosts(id)
    local entity=E.entity(id);local state=entity and entity.Vars.ESC_State
    if not state then return end
    id=E.uuid(entity) or id
    local native,seen={},{}
    local function include(handle)
        if seen[handle] then return end;seen[handle]=true
        local boost=E.entity(handle);local info=boost and boost.BoostInfo
        local cause=info and info.Cause and tostring(info.Cause.Cause)
        local params=info and info.Params
        if cause and params then
            native[cause]=native[cause] or {}
            local key=boostDescriptionKey(params.Boost,params.Params)
            native[cause][key]=(native[cause][key] or 0)+1
        end
    end
    for _,group in pairs(entity.BoostsContainer and entity.BoostsContainer.Boosts or {}) do
        for _,handle in pairs(group.Boosts) do include(handle) end
    end
    -- A false conditional bonus is still installed. Include its native handle
    -- even when it does not currently contribute to the active boost container.
    for _,row in pairs(entity.BoostConditionalState and entity.BoostConditionalState.States or {}) do include(row.Boost) end
    for slot,wanted in pairs(state.boosts or {}) do
        local submitted=submittedBoosts[id] and submittedBoosts[id][slot]
        if type(wanted)=='string' and wanted~='' and submitted~=wanted then
            local statements=boostStatements(wanted)
            if statements then
                local have=native['ESC_'..slot] or {};local missing={}
                for _,statement in ipairs(statements) do
                    if (have[statement.key] or 0)>0 then have[statement.key]=have[statement.key]-1
                    else missing[#missing+1]=statement.text end
                end
                if #missing>0 then
                    submittedBoost(id,slot,wanted)
                    -- Partial bundles restore only their absent statements.
                    -- Existing HP/AC/etc. are never removed or added twice.
                    Osi.AddBoosts(id,table.concat(missing,';'),'ESC_'..slot,id)
                end
            else E.log('Cannot reconcile unsupported saved boost slot '..slot) end
        end
    end
end
function E.isSword(item)
    if not item then return nil end
    for _,group in ipairs({'Longswords','Shortswords','Greatswords','Rapiers','Scimitars'}) do
        if Osi.IsEquipmentWithProficiency(item,group)==1 then return item end
    end
end
function E.sword(id,offhand)
    if not E.character(id) then return nil end
    return E.isSword(Osi.GetEquippedItem(id,offhand and 'Melee Offhand Weapon' or 'Melee Main Weapon'))
end
-- Technique foundations choose exactly one sword; ordinary attacks retain E.sword's hand.
function E.preferredSword(id)
    local main=E.sword(id);if main then return main,'main' end
    local off=E.sword(id,true);if off then return off,'off' end
    return nil,'qi'
end
function E.shield(id)
    if not E.character(id) then return nil end
    -- GetEquippedShield failure returns a truthy NULL GUID string in the client.
    -- Query the documented Shield slot and validate the actual equipment kind.
    local item=Osi.GetEquippedItem(id,'Shield');if not item then return nil end
    if Osi.IsEquipmentWithProficiency(item,'Shields')==1 then return item end
    local entity=E.entity(item)
    return entity and entity.Armor and entity.Armor.Shield==true and item or nil
end
function E.allowed(id,branch,offensive)
    if not E.character(id) or E.shield(id) then return false end
    if branch=='taixuan' or branch=='xingge' then
        local armor=Osi.GetEquippedItem(id,'Breast')
        if armor and (Osi.IsEquipmentWithProficiency(armor,'MediumArmor')==1
            or Osi.IsEquipmentWithProficiency(armor,'HeavyArmor')==1) then return false end
    end
    return not offensive or E.sword(id)~=nil or E.sword(id,true)~=nil or E.class(id)>0
end
function E.spellName(value)
    if type(value)=='string' then return value end
    return value and value.Prototype or nil
end
function E.useSpell(id,spell,target)
    -- Signature from the installed SharedDev story_header.div: five arguments.
    Osi.UseSpell(id,spell,target or id,'NULL_00000000-0000-0000-0000-000000000000',1)
end
function E.visible(a,b) return Osi.CanSee(a,b)==1 and Osi.HasLineOfSight(a,b)==1 end
function E.distance(a,b)
    local p,q=E.position(a),E.position(b)
    if not p or not q then return math.huge end
    return math.sqrt((p[1]-q[1])^2+(p[2]-q[2])^2+(p[3]-q[3])^2)
end
function E.tempHp(id)
    local entity=E.entity(id)
    return entity and entity.Health and entity.Health.TemporaryHp or 0
end
function E.forceImmune(id)
    local entity=E.entity(id)
    -- BG3 DamageType.Force=13; engine arrays are exposed to Lua with 1-based indices.
    local flags=entity and entity.Resistances and entity.Resistances.Resistances[14]
    -- BG3SE v32 exposes ResistanceBoostFlags as a bitfield userdata.
    if type(flags)=='userdata' then return flags.ImmuneToMagical end
    if type(flags)=='number' then return (flags & 4)~=0 end
    if type(flags)=='string' then return flags:find('ImmuneToMagical',1,true)~=nil end
    if type(flags)=='table' then
        for _,flag in pairs(flags) do if flag=='ImmuneToMagical' then return true end end
    end
    return false
end
function E.damageTransfer(id,amount,damageType,source)
    -- Installed Patch 8 call signature; this retains normal damage/temporary HP/
    -- concentration/death handling instead of treating damage as a HP assignment.
    -- SE enum userdata stringify to their label; Osiris STRING inputs do not
    -- perform that conversion themselves. Keep native hit enums unchanged.
    Osi.ApplyDamage(id,amount,tostring(damageType or 'Force'),source or id)
end
function E.hasPassive(id,name) return Osi.HasPassive(id,name)==1 end
function E.weaponWisdomCauses(item,owner)
    local entity=E.entity(item)
    local causes,seen={},{}
    for _,entry in pairs(entity and entity.BoostsContainer and entity.BoostsContainer.Boosts or {}) do
        if entry.Type=='WeaponAttackRollAbilityOverride' then for _,handle in pairs(entry.Boosts or {}) do
            local boost=E.entity(handle);local info=boost and boost.BoostInfo
            local ability=boost and boost.WeaponAttackRollAbilityOverrideBoost and boost.WeaponAttackRollAbilityOverrideBoost.Ability
            local cause=info and info.Cause and tostring(info.Cause.Cause) or ''
            local prefix='ESC_WEAPON_WISDOM_'
            if cause:find(prefix,1,true)==1 and E.sameEntity(cause:sub(#prefix+1),owner) and (ability=='Wisdom' or ability==5) and not seen[cause] then
                causes[#causes+1]=cause;seen[cause]=true
            end
        end end
    end
    return causes
end
function E.hasWeaponWisdom(item,cause)
    local prefix='ESC_WEAPON_WISDOM_'
    return cause:find(prefix,1,true)==1 and #E.weaponWisdomCauses(item,cause:sub(#prefix+1))>0
end
function E.swordAttribute(id,offhand)
    local weapon=E.sword(id,offhand)
    local entity=E.entity(weapon)
    local flags=entity and entity.Weapon and entity.Weapon.WeaponProperties or 0
    local finesse=type(flags)=='number' and (flags & 4)~=0
    local ordinary=finesse and math.max(E.ability(id,'Strength'),E.ability(id,'Dexterity')) or E.ability(id,'Strength')
    local override
    for _,entry in pairs(entity and entity.BoostsContainer and entity.BoostsContainer.Boosts or {}) do
        if entry.Type=='WeaponAttackRollAbilityOverride' then for _,handle in pairs(entry.Boosts or {}) do
            local boost=E.entity(handle);local info=boost and boost.BoostInfo
            local cause=info and info.Cause and tostring(info.Cause.Cause) or ''
            local ability=boost and boost.WeaponAttackRollAbilityOverrideBoost and boost.WeaponAttackRollAbilityOverrideBoost.Ability
            if ability and cause:find('ESC_WEAPON_WISDOM_',1,true)~=1 then
                if ability=='SpellCastingAbility' then local actor=E.entity(id);ability=actor and actor.Stats and actor.Stats.SpellCastingAbility end
                if type(ability)=='number' then ability=({'Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'})[ability] end
                if ability=='Strength' or ability=='Dexterity' or ability=='Constitution' or ability=='Intelligence' or ability=='Wisdom' or ability=='Charisma' then
                    override=math.max(override or -100,E.ability(id,ability))
                end
            end
        end end
    end
    if override then ordinary=override end
    return math.max(ordinary,E.ability(id,'Wisdom')),ordinary
end
function E.techniqueAttribute(id,offhand)
    local sword,hand=E.preferredSword(id)
    if offhand then sword,hand=E.sword(id,true),'off' end
    if not sword then return E.ability(id,'Wisdom'),hand end
    return E.swordAttribute(id,hand=='off'),hand
end
function E.setResource(id,uuid,amount)
    if not uuid then return false end
    local row=E.resourceEntry(id,uuid);if not row then return false end
    row.Amount=math.max(0,amount);row.MaxAmount=math.max(row.MaxAmount,row.Amount)
    E.entity(id):Replicate('ActionResources');return true
end
function E.freeOptions(id,target)
    if not E.alive(id) or not E.alive(target) or not E.visible(id,target) then return {} end
    for _,status in ipairs({'DOWNED','STUNNED','PARALYZED','SLEEPING','SLEEP','HOLD_PERSON','HOLD_MONSTER'}) do
        if E.hasStatus(id,status) then return {} end
    end
    local melee=Osi.GetEquippedWeapon(id)
    local options,seen={},{}
    local function add(spell,label)
        if not seen[spell] then options[#options+1]={spell=spell,label=label};seen[spell]=true end
    end
    if melee and E.distance(id,target)<=3 then add('Target_MainHandAttack','普通主手近战攻击') end
    if Osi.GetEquippedItem(id,'Melee Offhand Weapon') and E.distance(id,target)<=3 then add('Target_OffhandAttack','普通副手近战攻击') end
    if Osi.GetEquippedItem(id,'Ranged Main Weapon') and E.distance(id,target)<=18 then add('Projectile_MainHandAttack','普通主手远程攻击') end
    local entity=E.entity(id)
    for _,entry in pairs(entity and entity.SpellBook and entity.SpellBook.Spells or {}) do
            local name=E.spellName(entry.Id or entry.SpellId)
            local stat=name and Ext.Stats.Get(name)
            -- Weapon actions also have Level=0. The native IsSpell flag,
            -- returned as a string list by Stats.Get, identifies a cantrip.
            local isSpell=false;local flags=stat and stat.SpellFlags
            if type(flags)=='string' then isSpell=(';'..flags..';'):find(';IsSpell;',1,true)~=nil
            else for _,flag in pairs(flags or {}) do if flag=='IsSpell' then isSpell=true end end end
            local hasDamage,unsafe=false,false
            for _,field in ipairs({'SpellProperties','SpellSuccess','SpellFail'}) do
                -- Native Fire Bolt/Shocking Grasp place damage in SpellSuccess.
                local properties=stat and stat[field]
                if type(properties)=='string' then
                    hasDamage=hasDamage or properties:find('DealDamage',1,true)~=nil
                    unsafe=unsafe or properties:find('CreateSurface',1,true)~=nil or properties:find('CreateExplosion',1,true)~=nil or properties:find('SpawnExtraProjectiles',1,true)~=nil
                elseif properties then pcall(function()
                    for _,functorGroup in pairs(properties) do for _,functor in pairs(functorGroup.Functors or {}) do
                        local kind=tostring(functor.TypeId)
                        if kind=='DealDamage' then hasDamage=true end
                        if kind=='CreateSurface' or kind=='CreateExplosion' or kind=='SpawnExtraProjectiles' then unsafe=true end
                    end end
                end) end
            end
            local amount=stat and stat.AmountOfTargets;local single=amount==nil or amount=='' or tonumber(amount)==1
            local radius=stat and tonumber(stat.TargetRadius)
            if stat and isSpell and tonumber(stat.Level)==0 and stat.SpellRoll~='' and hasDamage
                and (stat.SpellType=='Target' or stat.SpellType=='Projectile') and single and not unsafe
                and not (E.classSpellKeys or {})[name]
                and (not radius or E.distance(id,target)<=radius) and not name:find('ESC_FREE_',1,true) then
                local label='单体伤害戏法'
                if Ext.Loca and stat.DisplayName then
                    local ok,value=pcall(Ext.Loca.GetTranslatedString,stat.DisplayName)
                    if ok and value and value~='' then label=value end
                end
                add(name,label)
            end
    end
    return options
end
function E.freeAttack(id,target,selection)
    local template
    for _,option in ipairs(E.freeOptions(id,target)) do if not selection or option.spell==selection then template=option.spell;break end end
    if not template then return false end
    local name='ESC_FREE_'..template
    if not Ext.Stats.Get(name,nil,false) then
        local stat=Ext.Stats.Create(name,'SpellData',template)
        stat.UseCosts='';stat.Cooldown='';stat:Sync()
    end
    E.useSpell(id,name,target)
    return true
end
function E.log(message) Ext.Utils.Print('[ESC] '..message) end
return E
