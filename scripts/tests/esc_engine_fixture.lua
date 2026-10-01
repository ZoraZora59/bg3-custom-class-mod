-- Test-only BG3 boundary. Production Engine.lua and Runtime.lua run unchanged.
-- This fixture deliberately does not emulate BG3's native attack/status engine.
Fixture = {entities={},listeners={},events={},timers={},calls={},stats={},listenerSignatures={},jsonPackets={},jsonCounter=0}
local F=Fixture
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
function Ext.Entity.Get(id) return type(id)=='table' and id or F.entities[id] end
function Ext.Entity.GetAllEntitiesWithComponent(component)
    local result={}
    for _,entity in pairs(F.entities) do
        if entity.Uuid and (component~='Classes' or #entity.Classes.Classes>0) then result[#result+1]=entity end
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
function Osi.IsInCombat(id) return F.entities[id]._combat and 1 or 0 end
function Osi.IsCharacter(id) return F.entities[id] and F.entities[id].Uuid and 1 or 0 end
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
function Osi.GetOwner(id) return F.entities[id]._owner end
function Osi.IsEquipped(id) return F.entities[id]._equipped and 1 or 0 end
function Osi.Equip(owner,item,addOnFail,notification,clearOwner)
    record('Equip',owner,item,addOnFail,notification,clearOwner)
end
function Osi.GetReservedUserID(id) return F.entities[id]._user end
function Osi.HasSpell(id,spell) return (F.entities[id]._spells or {})[spell] and 1 or 0 end
function Osi.RemoveSpell(id,spell,removeContainerSpells)
    record('RemoveSpell',id,spell,removeContainerSpells)
    if F.entities[id]._spells then F.entities[id]._spells[spell]=nil end
end
function Osi.UseSpell(source,spell,target,originator,withoutMove)
    record('UseSpell',source,spell,target,originator,withoutMove)
end
function Osi.IsEquipmentWithProficiency(id,name)
    return F.entities[id] and (F.entities[id]._proficiencies or {})[name] and 1 or 0
end
function Osi.AddBoosts(id,boost,slot,source)
    F.entities[id]._boosts[slot]=boost;record('AddBoosts',id,boost,slot,source)
end
function Osi.RemoveBoosts(id,boost,unused,slot,source)
    F.entities[id]._boosts[slot]=nil;record('RemoveBoosts',id,boost,slot,source)
end
function Osi.HasActiveStatus(id,name)
    return F.entities[id].StatusContainer.Statuses[name] and 1 or 0
end
function Osi.ApplyStatus(id,name,duration,force,source)
    record('ApplyStatus',id,name,duration,force,source)
    F.entities[id].StatusContainer.Statuses[name]={StatusId=name,Duration=duration,Source=source}
end
function Osi.RemoveStatus(id,name,source)
    record('RemoveStatus',id,name,source);F.entities[id].StatusContainer.Statuses[name]=nil
end
function F.resource(id) return F.entities[id].ActionResources.Resources[GeneratedSpec.resource][1] end
function F.callCount(name)
    local n=0;for _,call in ipairs(F.calls) do if call.name==name then n=n+1 end end;return n
end
function F.clearCalls() F.calls={} end
