import { DefaultPalette, IStackItemStyles, IStackStyles, Stack } from "@fluentui/react";
import moment from "moment";
import React from "react";
import { Resource } from "../../models/resource";

interface ResourcePropertyPanelProps {
    resource: Resource
}

interface ResourcePropertyPanelItemProps {
    header: String,
    val: String
}

export const ResourcePropertyPanelItem: React.FunctionComponent<ResourcePropertyPanelItemProps> = (props: ResourcePropertyPanelItemProps) => {
    
    const stackItemStyles: IStackItemStyles = {
        root: {
            padding: 5,
            width: 150,
            color: DefaultPalette.neutralSecondary
        }
    }

    function renderValue(val: String) {
        if (val.startsWith('https://')) {
            return (<a href={val.toString()} target='_blank' rel="noreferrer">{val}</a>)
        }
        return val;
    }

    return(
        <>
            <Stack wrap horizontal>
                <Stack.Item grow styles={stackItemStyles}>
                    {props.header}
                </Stack.Item>
                <Stack.Item grow={3} styles={stackItemStyles}>
                    : { renderValue(props.val)}
                </Stack.Item>
            </Stack>
        </>
    );
}

export const ResourcePropertyPanel: React.FunctionComponent<ResourcePropertyPanelProps> = (props: ResourcePropertyPanelProps) => {
    
    const stackStyles: IStackStyles = {
        root: {
            padding: 0,
            minWidth: 300
        }
    };

    function userFriendlyKey(key: String){
        let friendlyKey = key.replaceAll('_', ' ');
        return friendlyKey.charAt(0).toUpperCase() + friendlyKey.slice(1).toLowerCase();
    }

    return (
        <>
            <Stack wrap horizontal>
                <Stack grow styles={stackStyles}>
                    <ResourcePropertyPanelItem header={'Resource ID'} val={props.resource.id} />
                    <ResourcePropertyPanelItem header={'Resource type'} val={props.resource.resourceType} />
                    <ResourcePropertyPanelItem header={'Resource path'} val={props.resource.resourcePath} />
                    <ResourcePropertyPanelItem header={'Template name'} val={props.resource.templateName} />
                    <ResourcePropertyPanelItem header={'Template version'} val={props.resource.templateVersion} />
                    <ResourcePropertyPanelItem header={'Is active'} val={props.resource.isActive.toString()} />
                    <ResourcePropertyPanelItem header={'Is enabled'} val={props.resource.isEnabled.toString()} />
                    <ResourcePropertyPanelItem header={'User'} val={props.resource.user.name} />
                    <ResourcePropertyPanelItem header={'Last updated'} val={moment.unix(props.resource.updatedWhen).toDate().toDateString()} />
                </Stack>    
                <Stack grow styles={stackStyles}>
                {
                    Object.keys(props.resource.properties).map((key) => {
                        let val = (props.resource.properties as any)[key].toString();
                        return (
                            <ResourcePropertyPanelItem header={userFriendlyKey(key)} val={val} key={key}/>
                        )
                    })
                }
                </Stack>
            </Stack>
        </>
    );
};
