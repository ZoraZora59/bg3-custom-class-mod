-- Presentation only. Native MirrorImage overlays copy the equipped visual;
-- there are no actors, attacks, timers, status/resource writes or chain writes.
local M={}
function M.Install(E,spec)
    local config=spec.xueyanEchoVfx
    if not config or not config.enabled then return end
    local records=config.records or {}
    local seen,order={},{}
    local function begin(id,spell,action)
        spell=E.spellName(spell)
        local alias=(spec.aliases or {})[spell]
        if not alias or alias.key~='xueyan_wusheng' or alias.internal then return end
        local _,branch=E.class(id)
        if branch~='xueyan' or not E.alive(id) then return end
        local entity=E.entity(id)
        local uuid=E.uuid(entity)
        if not uuid then return end
        local key='intro'
        if alias.continuation then
            -- UsingSpell precedes CastedSpell's decrement. Root is sword 1;
            -- remaining 5,4,3,2,1 identifies swords 2,3,4,5,6 respectively.
            local state=entity.Vars and entity.Vars.ESC_State
            local chain=state and state.chains and state.chains.wusheng
            local n=chain and tonumber(chain.remaining)
            if not n or n<1 or n>5 or n~=math.floor(n) then return end
            key='echo'..tostring(math.floor((6-n)/2)+1)
        end
        local row=records[key]
        if not row or not row.effect then return end
        local token=uuid:lower()..':'..tostring(action)..':'..spell
        if seen[token] then return end
        seen[token]=true;order[#order+1]=token
        if #order>128 then seen[table.remove(order,1)]=nil end
        -- Installed story_header.div: object, EFFECTRESOURCE, bone, scale.
        -- Bounded one-shots end in <=1.8s even if the cast fails or chain ends.
        pcall(Osi.PlayEffect,id,row.effect,'Dummy_Root',1)
    end
    Ext.Osiris.RegisterListener('UsingSpell',5,'before',function(id,spell,kind,element,action) begin(id,spell,action) end)
    Ext.Osiris.RegisterListener('UsingSpellOnTarget',6,'before',function(id,target,spell,kind,element,action) begin(id,spell,action) end)
    Ext.Events.SessionLoaded:Subscribe(function() seen={};order={} end)
end
return M
