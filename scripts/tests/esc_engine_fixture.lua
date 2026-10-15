-- Test-only BG3 boundary. Production Engine.lua and Runtime.lua run unchanged.
-- This fixture deliberately does not emulate BG3's native attack/status engine.
Fixture = {entities={},listeners={},events={},entityEvents={},timers={},nextTicks={},calls={},stats={},listenerSignatures={},jsonPackets={},jsonCounter=0}
local F=Fixture
-- Shared shield fixture is actual equipment, not merely a string in a slot.
F.entities.shield={_isItem=true,_boosts={},_proficiencies={Shields=true},Armor={Shield=true}}
function F.strictProxy(values)
    return setmetatable({}, {__index=function(_,key)
        local value=values[key]
        if value==nil then error('Property does not exist: '..tostring(key)) end
        return value
    end})
end
function F.strictEntity(id)
    local values=assert(F.entities[id],id)
    local knownComponents={Classes=true,Weapon=true,BoostsContainer=true,Stats=true,
        Transform=true,ActionResources=true,Health=true,IsItem=true,Vars=true,Uuid=true}
    local proxy=setmetatable({}, {__index=function(_,key)
        local value=values[key]
        if value==nil and not knownComponents[key] then
            error('Not a valid EntityProxy method or component type: '..tostring(key))
        end
        return value
    end})
    F.entities[id]=proxy
    return proxy
end
local function record(name,...)
    F.calls[#F.calls+1]={name=name,args={...}}
end
function F.emit(name,...)
    for _,callback in ipairs(F.listeners[name] or {}) do callback(...) end
end
function F.event(name,evt)
    for _,callback in ipairs(F.events[name] or {}) do callback(evt) end
    -- Most focused tests advance to the event-loop boundary automatically. The
    -- restricted-context regression holds this queue until it leaves loading.
    if not F.deferNextTicks then F.runNextTick() end
end
function F.runNextTick()
    local callbacks=F.nextTicks;F.nextTicks={}
    for _,callback in ipairs(callbacks) do callback() end
end
function F.actor(id,level,branch,hp,maxHp,party,x)
    local entity={Uuid={EntityUuid=id},Vars={},Classes={Classes={}},
        ActionResources={Resources={}},Transform={Transform={Translate={x or 0,0,0}}},
        StatusContainer={Statuses={}},_hp=hp or 100,_maxHp=maxHp or 100,
        _party=party,_combat=true,_dead=false,_isItem=false,_user=0x10001,TurnBased={IsActiveCombatTurn=true},_abilities={Wisdom=20,Strength=16,Dexterity=14,Constitution=16},
        _equipped={},_boosts={}}
    entity._equipped['Melee Main Weapon']='sword:'..id
    function entity:Replicate(name) record('Replicate',id,name) end
    F.entities[id]=entity
    F.entities['sword:'..id]={_isItem=true,_owner=id,_proficiencies={Longswords=true},_boosts={}}
    if level and level>0 then
        entity.Classes.Classes={{ClassUUID=GeneratedSpec.classes.common,SubClassUUID=GeneratedSpec.classes[branch],Level=level}}
        entity.ActionResources.Resources[GeneratedSpec.resource]={{Level=0,Amount=0,MaxAmount=50}}
        entity.ActionResources.Resources['45ff0f48-b210-4024-972f-b64a44dc6985']={{Level=0,Amount=1,MaxAmount=1}}
        entity.ActionResources.Resources['420c8df5-45c2-4253-93c2-7ec44e127930']={{Level=0,Amount=1,MaxAmount=1}}
        entity.ActionResources.Resources['734cbcfb-8922-4b6d-8330-b2a7e4c14b6a']={{Level=0,Amount=1,MaxAmount=1}}
        if level>=5 then
            if GeneratedSpec.opportunityResource then entity.ActionResources.Resources[GeneratedSpec.opportunityResource]={{Level=0,Amount=0,MaxAmount=4}} end
            if GeneratedSpec.flightResource then entity.ActionResources.Resources[GeneratedSpec.flightResource]={{Level=0,Amount=0,MaxAmount=24}} end
            if GeneratedSpec.chainMoveResource then entity.ActionResources.Resources[GeneratedSpec.chainMoveResource]={{Level=0,Amount=0,MaxAmount=6}} end
        end
    end
    return entity
end
Ext={Entity={},Vars={},Json={},IO={},Stats={},Timer={},Utils={},Osiris={},ServerNet={},ClientNet={}}
function Ext.Entity.OnCreate(name,callback)
    F.entityEvents[name]=F.entityEvents[name] or {};table.insert(F.entityEvents[name],callback)
    return #F.entityEvents[name]
end
function F.entityCreated(name,component)
    for _,callback in ipairs(F.entityEvents[name] or {})do callback(nil,name,component)end
end
function Ext.Entity.Get(id) return type(id)=='table' and id or F.entities[id] end
function Ext.Entity.GetAllEntitiesWithComponent(component)
    local result={}
    for _,entity in pairs(F.entities) do
        if entity.Uuid and (component~='Classes' or entity.Classes~=nil) then result[#result+1]=entity end
    end
    return result
end
function Ext.Vars.RegisterUserVariable(...) record('RegisterUserVariable',...) end
function Ext.Json.Parse(value)
    if type(value)=='table' then return value end
    if value=='{}' then return GeneratedSpec end
    if F.jsonPackets[value] then return F.jsonPackets[value] end
    error('Mock native JSON parser: malformed input')
end
function Ext.Json.Stringify(value)
    F.jsonCounter=F.jsonCounter+1;local key='json-packet-'..F.jsonCounter
    F.jsonPackets[key]=value;return key
end
function Ext.ServerNet.PostMessageToClient(id,channel,payload) record('PostMessageToClient',id,channel,payload) end
function Ext.ServerNet.PostMessageToUser(user,channel,payload) record('PostMessageToUser',user,channel,payload) end
function Ext.ClientNet.PostMessageToServer(channel,payload) record('PostMessageToServer',channel,payload) end
function Ext.IO.LoadFile(...) return '{}' end
function Ext.IO.SaveFile(path,data) record('SaveFile',path,data);return true end
function Ext.Stats.Get(name) return F.stats[name] end
function Ext.Stats.Create(name,kind,prototype)
    local row={};for key,value in pairs(F.stats[prototype] or {}) do row[key]=value end
    function row:Sync() record('StatsSync',name) end
    F.stats[name]=row;record('StatsCreate',name,kind,prototype);return row
end
function Ext.Timer.WaitFor(ms,callback) F.timers[#F.timers+1]={ms=ms,callback=callback} end
function Ext.OnNextTick(callback) F.nextTicks[#F.nextTicks+1]=callback end
function Ext.Utils.Print(message) record('Print',message) end
function Ext.Osiris.RegisterListener(name,arity,when,callback)
    F.listenerSignatures[#F.listenerSignatures+1]={name=name,arity=arity,when=when}
    F.listeners[name]=F.listeners[name] or {}
    F.listeners[name][#F.listeners[name]+1]=callback
end
Ext.Events=setmetatable({}, {__index=function(self,name)
    local event={}
    function event:Subscribe(callback)
        F.events[name]=F.events[name] or {}
        F.events[name][#F.events[name]+1]=callback
    end
    rawset(self,name,event)
    return event
end})
Osi={}
function Osi.GetHitpoints(id) return assert(F.entities[id],id)._hp end
function Osi.GetMaxHitpoints(id) return assert(F.entities[id],id)._maxHp end
function Osi.SetHitpoints(id,value,mode)
    record('SetHitpoints',id,value,mode);F.entities[id]._hp=value
end
function Osi.ApplyDamage(id,amount,damageType,source)
    -- Native Osiris STRING arguments reject SE enum userdata rather than
    -- applying Lua's tostring implicitly (H25 live transfer failure).
    assert(type(damageType)=='string','ApplyDamage DamageType: String expected, got '..type(damageType))
    record('ApplyDamage',id,amount,damageType,source)
    local hit={DamageList={{Amount=amount,DamageType=damageType}},TotalDamageDone=amount}
    local event={Caster=source,Target=id,StoryActionId=F.transferAction or 0,Hit=hit}
    if F.transferHooks then hit.SpellId='Target_MainHandAttack';F.event('DealDamage',event) end
    F.event('BeforeDealDamage',{Hit=hit})
    -- Simulate native HP application only. Class/aura/transfer percentages are
    -- production Runtime work; gear resistance/immunity/temp HP are not modeled.
    F.entities[id]._hp=math.max(0,F.entities[id]._hp-hit.TotalDamageDone)
    if F.transferHooks then event.Result={Hit=hit};F.event('DealtDamage',event) end
end
function Osi.GetAbility(id,name) return F.entities[id]._abilities[name] or 10 end
function Osi.IsDead(id) return F.entities[id]._dead and 1 or 0 end
function Osi.IsOnStage(id) return F.entities[id] and F.entities[id]._onStage~=false and 1 or 0 end
function Osi.IsInCombat(id) return F.entities[id]._combat and 1 or 0 end
function Osi.IsCharacter(id) return F.entities[id] and F.entities[id].Uuid and 1 or 0 end
function Osi.IsPlayer(id) return F.entities[id]._player==false and 0 or F.entities[id]._party=='players' and 1 or 0 end
function Osi.IsItem(id) return F.entities[id] and F.entities[id]._isItem and 1 or 0 end
function Osi.IsInPartyWith(a,b)
    local pa,pb=F.entities[a]._party,F.entities[b]._party
    return pa and pa==pb and 1 or 0
end
function Osi.IsEnemy(a,b) return F.entities[a]._party~=F.entities[b]._party and 1 or 0 end
function Osi.GetEquippedItem(id,slot) return F.entities[id]._equipped[slot] end
function Osi.GetEquippedShield(id) return F.entities[id]._equipped.Shield end
function Osi.GetEquippedWeapon(id) return F.entities[id]._equipped['Melee Main Weapon'] end
function Osi.IsSummon(id) return F.entities[id]._summon and 1 or 0 end
function Osi.CanSee(a,b) return F.entities[a]._cannotSee~=b and 1 or 0 end
function Osi.HasLineOfSight(a,b) return F.entities[a]._blocked~=b and 1 or 0 end
function Osi.HasPassive(id,name) return (F.entities[id]._passives or {})[name] and 1 or 0 end
function Osi.AddPassive(id,name)
    record('AddPassive',id,name)
    local entity=F.entities[id];entity._passives=entity._passives or {};entity._passives[name]=true
end
function Osi.RemovePassive(id,name)
    record('RemovePassive',id,name)
    if F.entities[id]._passives then F.entities[id]._passives[name]=nil end
end
function Osi.GetOwner(id) return F.entities[id]._owner end
function Osi.GetReservedUserID(id) return F.entities[id]._user end
function Osi.HasSpell(id,spell) return (F.entities[id]._spells or {})[spell] and 1 or 0 end
function Osi.AddSpell(id,spell,showNotification,addContainerSpells)
    record('AddSpell',id,spell,showNotification,addContainerSpells)
    local entity=F.entities[id];entity._spells=entity._spells or {};entity._spells[spell]=true
    local children=F.stats[spell] and F.stats[spell].ContainerSpells
    if addContainerSpells~=0 and type(children)=='string' then
        for child in children:gmatch('[^;]+') do entity._spells[child]=true end
    end
end
function Osi.RemoveSpell(id,spell,removeContainerSpells)
    record('RemoveSpell',id,spell,removeContainerSpells)
    local spells=F.entities[id]._spells
    if spells then
        spells[spell]=nil
        local children=F.stats[spell] and F.stats[spell].ContainerSpells
        if removeContainerSpells~=0 and type(children)=='string' then
            for child in children:gmatch('[^;]+') do spells[child]=nil end
        end
    end
end
function Osi.UseSpell(source,spell,target,originator,withoutMove)
    record('UseSpell',source,spell,target,originator,withoutMove)
end
function Osi.IsEquipmentWithProficiency(id,name)
    return F.entities[id] and (F.entities[id]._proficiencies or {})[name] and 1 or 0
end
function Osi.AddBoosts(id,boost,slot,source)
    F.entities[id]._boosts[slot]=boost;record('AddBoosts',id,boost,slot,source)
    if boost=='WeaponAttackRollAbilityOverride(Wisdom)' then
        local item=F.entities[id];item.BoostsContainer=item.BoostsContainer or {Boosts={}}
        local handle='fixture-weapon-boost:'..id..':'..slot
        F.entities[handle]={BoostInfo={Cause={Cause=slot}},WeaponAttackRollAbilityOverrideBoost={Ability='Wisdom'}}
        local entries=item.BoostsContainer.Boosts;local group
        for _,entry in pairs(entries) do if entry.Type=='WeaponAttackRollAbilityOverride' then group=entry end end
        if not group then group={Type='WeaponAttackRollAbilityOverride',Boosts={}};entries[#entries+1]=group end
        for _,old in pairs(group.Boosts) do if old==handle then return end end
        group.Boosts[#group.Boosts+1]=handle
    end
end
function Osi.RemoveBoosts(id,boost,unused,slot,source)
    F.entities[id]._boosts[slot]=nil;record('RemoveBoosts',id,boost,slot,source)
    if boost=='WeaponAttackRollAbilityOverride(Wisdom)' then
        local item=F.entities[id]
        for _,entry in pairs(item.BoostsContainer and item.BoostsContainer.Boosts or {}) do
            if entry.Type=='WeaponAttackRollAbilityOverride' then
                local remaining={}
                for _,handle in pairs(entry.Boosts or {}) do
                    local native=F.entities[handle];local cause=native and native.BoostInfo and native.BoostInfo.Cause
                    if not cause or cause.Cause~=slot then remaining[#remaining+1]=handle else F.entities[handle]=nil end
                end
                entry.Boosts=remaining
            end
        end
    end
end
function Osi.HasActiveStatus(id,name)
    for _,status in pairs(F.entities[id].StatusContainer.Statuses) do
        if status==name or type(status)=='table' and status.StatusId==name then return 1 end
    end
    return 0
end
function Osi.ApplyStatus(id,name,duration,force,source)
    record('ApplyStatus',id,name,duration,force,source)
    F.entities[id].StatusContainer.Statuses[name]={StatusId=name,Duration=duration,Source=source,StatusSource=source}
end
function Osi.RemoveStatus(id,name,source)
    record('RemoveStatus',id,name,source)
    for handle,status in pairs(F.entities[id].StatusContainer.Statuses) do
        if status==name or type(status)=='table' and status.StatusId==name then F.entities[id].StatusContainer.Statuses[handle]=nil end
    end
end
function F.resource(id) return F.entities[id].ActionResources.Resources[GeneratedSpec.resource][1] end
function F.callCount(name)
    local n=0;for _,call in ipairs(F.calls) do if call.name==name then n=n+1 end end;return n
end
function F.clearCalls() F.calls={} end

-- Native OnHeal passive boundary. Actual recovered HP is an input from the
-- simulated engine, independent of Runtime. H28 paired action84/86 proves
-- Regain callbacks precede HP settlement; native OnHeal follows settlement,
-- retains rolled TotalHealDone even for full HP, then emits ECS HEAL/Osiris.
function F.nativeHeal(id,spell,target,action,requested,blocked)
    local params={Type='AttackTarget',Caster=id,Target=target,StoryActionId=action,
        SpellId={Prototype=spell},PropertyContext=F.nativeHealContext or {TARGET=true}}
    local evt={Params=params,Functor={FunctorList={{TypeId='RegainHitPoints',HealingType='Guaranteed'}}},
        Hit={Hit={TotalHealDone=0,StoryActionId=action}}}
    for _,callback in ipairs(F.events.ExecuteFunctor or {})do callback(evt)end
    for _,callback in ipairs(F.events.AfterExecuteFunctor or {})do callback(evt)end
    if F.beforeNativeHeal then local fn=F.beforeNativeHeal;F.beforeNativeHeal=nil;fn()end
    local before=Osi.GetHitpoints(target)
    local actual=not blocked and before>0 and math.max(0,math.min(requested,Osi.GetMaxHitpoints(target)-before)) or 0
    F.entities[target]._hp=before+actual
    local passive=F.stats.ESC_P_xingge_cooperation
    local level,branch=ESC.Engine.class(id)
    local marker
    if passive and passive.StatsFunctorContext=='OnHeal' and level>0 and branch=='xingge' then
        local env={HealDoneGreaterThan=function(n)return (not blocked and requested or 0)>n end,
            SpellId=function(name)return name==spell end,
            Self=function()return ESC.Engine.sameEntity(id,target)end,
            Party=function()return Osi.IsInPartyWith(id,target)==1 end,
            IsSummon=function()return Osi.IsSummon(target)==1 end}
        if assert(load('return '..passive.Conditions,'native-onheal-condition','t',env))() then
            marker=assert(passive.StatsFunctors:match('^ApplyStatus%((ESC_[A-Z0-9_]+),100,0%)$'))
            assert(F.stats[marker] and F.stats[marker].StatusType=='BOOST')
            local onheal={Params={Type='AttackTarget',Caster=id,Target=target,StoryActionId=action,SpellId={Prototype=spell},
                PropertyContext={HEAL=true},Hit={TotalHealDone=requested},
                Attack={InitialHPPercentage=math.ceil(before*100/Osi.GetMaxHitpoints(target)),TotalHealDone=requested}},
                Functor={FunctorList={{TypeId='ApplyStatus',StatusId=marker}}},Hit={Hit={TotalHealDone=requested}}}
            for _,callback in ipairs(F.events.ExecuteFunctor or {})do callback(onheal)end
            for _,callback in ipairs(F.events.AfterExecuteFunctor or {})do callback(onheal)end
        end
    end
    if not blocked then
        local entity=F.entities[target]
        entity._nativeHealStatus={Started=true,HealAmount=requested,TargetHealth=0,StoryActionID=action,StatusSource=id}
        entity.ServerCharacter={GetStatus=function(_,name)return name=='HEAL' and entity._nativeHealStatus or nil end}
        F.entityCreated('ServerStatusApplyEvent',{Target=target,StatusId='HEAL',Status=tostring(action)..':'..target})
        entity._nativeHealStatus=nil
    end
    if marker then F.emit('StatusApplied',target,marker,id,action)end
    return actual
end

-- Focused native boundary for guard/protection status functors. Deliberately
-- does not emulate attack rolls, status timing or native boost evaluation.
-- The recipient selector follows native Shared/Shout_HealingRadiance's
-- ApplyStatus(SELF,...) and Shared/Passive's RemoveStatus(SELF,...). The omitted
-- selector uses the actual target; SELF: is not granted invented semantics.
-- This small boundary is not a BG3 parser; native acceptance remains required.
function F.statusFunctors(id,spell,target,action)
    local properties=F.stats[spell] and F.stats[spell].SpellProperties or ''
    for functor in properties:gmatch('[^;]+') do
        if functor=='IF(Self() or (Party() and not IsSummon())):RegainHitPoints((Target.MaxHP*LevelMapValue(ESC_XiangfuHealing)+99)/100,Guaranteed)'
            and (id==target or Osi.IsInPartyWith(id,target)==1 and Osi.IsSummon(target)==0) then
            -- Independent native result boundary, not Engine.heal/SetHitpoints.
            -- Positive integer division follows shipped WholenessOfBody's
            -- (ClassLevel(Monk)+1)/2 ceiling convention, here denominator 100.
            local recipient=target or id
            local level=ESC.Engine.class(id)
            local amount=math.floor((Osi.GetMaxHitpoints(recipient)*(level<4 and 15 or 30)+99)/100)
            F.nativeHeal(id,spell,recipient,action,amount)
        end
        if functor:find('ESC_COUNTER_',1,true) or functor:find('ESC_XINGGE_PROTECTION',1,true) then
            assert(not functor:find('SELF:',1,true),'Unsupported SELF: prefix; use the native SELF argument')
            local condition=functor:match('IF%((.*)%):')
            local env={context={Source=id},HasStatus=function(name,source) return Osi.HasActiveStatus(source or id,name)==1 end}
            local enabled=not condition or assert(load('return '..condition,'native-status-condition','t',env))()
            if enabled then
                local name,rounds=functor:match('ApplyStatus%(%s*SELF%s*,%s*(ESC_[A-Z0-9_]+)%s*,%s*100%s*,%s*(%d+)%s*%)')
                local selfTarget=name~=nil
                if not name then name,rounds=functor:match('ApplyStatus%(%s*(ESC_[A-Z0-9_]+)%s*,%s*100%s*,%s*(%d+)%s*%)') end
                local removed=functor:match('RemoveStatus%(%s*SELF%s*,%s*(ESC_[A-Z0-9_]+)%s*%)')
                selfTarget=selfTarget or removed~=nil
                if not removed then removed=functor:match('RemoveStatus%(%s*(ESC_[A-Z0-9_]+)%s*%)') end
                assert(name or removed,'Unsupported guard/protection status functor: '..functor)
                local recipient=selfTarget and id or target or id
                if name then
                    Osi.ApplyStatus(recipient,name,tonumber(rounds)*6,1,id)
                    F.entities[recipient].StatusContainer.Statuses[name].StoryActionID=action
                    F.emit('StatusApplied',recipient,name,id,action)
                elseif removed and Osi.HasActiveStatus(recipient,removed)==1 then
                    Osi.RemoveStatus(recipient,removed,id)
                    F.emit('StatusRemoved',recipient,removed,id,action)
                end
            end
        end
    end
end

-- Explicit mirror of the native protection's declarative turn clock only.
-- This does not establish the engine's event ordering or live status timing.
function F.protectionTurnStarted(id)
    local definition=assert(F.stats.ESC_XINGGE_PROTECTION)
    assert(definition.TickType=='StartTurn')
    local sourceClock=(definition.StatusPropertyFlags or ''):find('TickingWithSource',1,true)~=nil
    for target,entity in pairs(F.entities) do
        local status=entity.StatusContainer and entity.StatusContainer.Statuses.ESC_XINGGE_PROTECTION
        if status then
            local clock=sourceClock and status.StatusSource or target
            if F.entities[clock]==F.entities[id] then
                status.Duration=status.Duration-6
                if status.Duration<=0 then
                    Osi.RemoveStatus(target,status.StatusId,status.StatusSource)
                    F.emit('StatusRemoved',target,status.StatusId,status.StatusSource,status.StoryActionID)
                end
            end
        end
    end
    F.emit('TurnStarted',id)
end
