import * as React from 'react';
import { List } from '@fluentui/react/lib/List';
import { ITheme, mergeStyleSets, getTheme, getFocusStyle } from '@fluentui/react/lib/Styling';
import { HistoryItem } from '../../models/resource';

const theme: ITheme = getTheme();
const { palette, semanticColors, fonts } = theme;

const classNames = mergeStyleSets({
  itemCell: [
    getFocusStyle(theme, { inset: -1 }),
    {
      minHeight: 54,
      padding: 10,
      boxSizing: 'border-box',
      borderBottom: `1px solid ${semanticColors.bodyDivider}`,
      display: 'flex',
      selectors: {
        '&:hover': { background: palette.neutralLight },
      },
    },
  ],
  itemImage: {
    flexShrink: 0,
  },
  itemContent: {
    marginLeft: 10,
    overflow: 'hidden',
    flexGrow: 1,
  },
  itemName: [
    fonts.xLarge,
    {
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
  ],
  itemIndex: {
    fontSize: fonts.small.fontSize,
    color: palette.neutralTertiary,
    marginBottom: 10,
  },
  chevron: {
    alignSelf: 'center',
    marginLeft: 10,
    color: palette.neutralTertiary,
    fontSize: fonts.large.fontSize,
    flexShrink: 0,
  },
});

interface ResourceHistoryProps {
  history: Array<HistoryItem>
}

const onRenderCell = (item: any, index: number | undefined): JSX.Element => {
  var propertyBag = {...item.properties}
  delete propertyBag['display_name']
  delete propertyBag['description']
  let val = JSON.stringify(propertyBag)

  return (
    <div className={classNames.itemCell} data-is-focusable={true}>
      <div className={classNames.itemContent}>
        <div className={classNames.itemName}>{item.properties.display_name}</div>
        <div className={classNames.itemIndex}>{`Item ${index}`}</div>
        <div>{item.properties.description}</div>
        <div>{val}</div>
      </div>
    </div>
  );
};

export const ResourceHistory: React.FunctionComponent<ResourceHistoryProps> = (props: ResourceHistoryProps) => {

  return (
    <>
    <hr />
      <List items={props.history} onRenderCell={onRenderCell} />
    </>    
  )
};