import React, { useCallback, useContext, useEffect, useState } from 'react';
import { ColumnActionsMode, CommandBarButton, ContextualMenu, DirectionalHint, getTheme, IColumn, IContextualMenuItem, IContextualMenuProps, Persona, PersonaSize, SelectionMode, ShimmeredDetailsList, Stack } from '@fluentui/react';
import { HttpMethod, useAuthApiCall } from '../../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../../models/apiEndpoints';
import { WorkspaceContext } from '../../../contexts/WorkspaceContext';
import { AirlockRequest, AirlockRequestAction, AirlockRequestStatus, AirlockRequestType } from '../../../models/airlock';
import moment from 'moment';
import { Route, Routes, useNavigate } from 'react-router-dom';
import { AirlockViewRequest } from './AirlockViewRequest';
import { LoadingState } from '../../../models/loadingState';
import { APIError } from '../../../models/exceptions';
import { ExceptionLayout } from '../ExceptionLayout';
import { AirlockNewRequest } from './AirlockNewRequest';

interface AirlockProps {
}

export const Airlock: React.FunctionComponent<AirlockProps> = (props: AirlockProps) => {
  const [airlockRequests, setAirlockRequests] = useState([] as AirlockRequest[]);
  const [requestColumns, setRequestColumns] = useState([] as IColumn[]);
  const [orderBy, setOrderBy] = useState('updatedWhen');
  const [orderAscending, setOrderAscending] = useState(false);
  const [filters, setFilters] = useState(new Map<string, string>());
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const [contextMenuProps, setContextMenuProps] = useState<IContextualMenuProps>();
  const [apiError, setApiError] = useState<APIError>();
  const workspaceCtx = useContext(WorkspaceContext);
  const apiCall = useAuthApiCall();
  const theme = getTheme();
  const navigate = useNavigate();

  // Get the airlock request data from API
  useEffect(() => {
    console.log('Getting airlock requests');
    const getAirlockRequests = async () => {
      setApiError(undefined);
      setLoadingState(LoadingState.Loading);

      try {
        let requests: AirlockRequest[];
        if (workspaceCtx.workspace) {

          // Add any selected filters and orderBy
          let query = '?';
          filters.forEach((value, key) => {
            query += `${key}=${value}&`;
          });
          if (orderBy) {
            query += `order_by=${orderBy}&order_ascending=${orderAscending}&`;
          }

          // Call the Airlock requests API
          console.log(`Calling ${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}${query.slice(0, -1)}`);
          const result = await apiCall(
            `${ApiEndpoint.Workspaces}/${workspaceCtx.workspace.id}/${ApiEndpoint.AirlockRequests}${query.slice(0, -1)}`,
            HttpMethod.Get,
            workspaceCtx.workspaceApplicationIdURI
          );
          console.log('Got requests', result);

          // Map the inner requests and the allowed user actions to state
          requests = result.airlockRequests.map((r: {
            airlockRequest: AirlockRequest,
            allowed_user_actions: Array<AirlockRequestAction>
          }) => {
            const request = r.airlockRequest;
            request.allowed_user_actions = r.allowed_user_actions;
            return request;
          });
        } else {
          // TODO: Get all requests across workspaces
          requests = [];
        }

        setAirlockRequests(requests);
        setLoadingState(LoadingState.Ok);
      } catch (err: any) {
        err.userMessage = 'Error fetching airlock requests';
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    }
    getAirlockRequests();
  }, [apiCall, workspaceCtx.workspace, workspaceCtx.workspaceApplicationIdURI, filters, orderBy, orderAscending]);

  const orderRequests = (column: IColumn) => {
    setOrderBy((o) => {
      // If already selected, invert ordering
      if (o === column.key) {
        setOrderAscending((previous) => !previous);
        return column.key;
      }
      return column.key;
    });
  };

  // Open a context menu in the requests list for filtering and sorting
  const openContextMenu = useCallback((column: IColumn, ev: React.MouseEvent<HTMLElement>, options: Array<string>) => {
    const filterOptions = options.map(option => {
      return {
        key: option,
        name: option,
        canCheck: true,
        checked: filters?.has(column.key) && filters.get(column.key) === option,
        onClick: () => {
          // Set filter or unset if already selected
          setFilters((f) => {
            if (f.get(column.key) === option) {
              f.delete(column.key);
            } else {
              f.set(column.key, option);
            }
            // Return as a new map to trigger re-rendering
            return new Map(f);
          });
        }
      }
    });

    const items: IContextualMenuItem[] = [
      {
          key: 'sort',
          name: 'Sort',
          iconProps: { iconName: 'Sort' },
          onClick: () => orderRequests(column)
      },
      {
        key: 'filter',
        name: 'Filter',
        iconProps: { iconName: 'Filter' },
        subMenuProps: {
          items: filterOptions,
        }
      }
    ];

    setContextMenuProps({
        items: items,
        target: ev.currentTarget as HTMLElement,
        directionalHint: DirectionalHint.bottomCenter,
        gapSpace: 0,
        onDismiss: () => setContextMenuProps(undefined),
    });
  }, [filters]);

  // Set the columns on initial render
  useEffect(() => {
    const orderByColumn = (ev: React.MouseEvent<HTMLElement>, column: IColumn) => {
      orderRequests(column);
    };

    const columns: IColumn[] = [
      {
        key: 'avatar',
        name: '',
        minWidth: 16,
        maxWidth: 16,
        isIconOnly: true,
        onRender: (request: AirlockRequest) => {
          return <Persona size={ PersonaSize.size24 } text={ request.user?.name } />
        }
      },
      {
        key: 'initiator',
        name: 'Initiator',
        ariaLabel: 'Creator of the airlock request',
        minWidth: 150,
        maxWidth: 200,
        isResizable: true,
        onRender: (request: AirlockRequest) => request.user?.name
      },
      {
        key: 'requestType',
        name: 'Type',
        ariaLabel: 'Whether the request is import or export',
        minWidth: 70,
        maxWidth: 100,
        isResizable: true,
        fieldName: 'requestType',
        columnActionsMode: ColumnActionsMode.hasDropdown,
        isSorted: orderBy === 'requestType',
        isSortedDescending: !orderAscending,
        onColumnClick: (ev, column) => openContextMenu(column, ev, Object.values(AirlockRequestType)),
        onColumnContextMenu: (column, ev) =>
          (column && ev) && openContextMenu(column, ev, Object.values(AirlockRequestType)),
        isFiltered: filters.has('requestType')
      },
      {
        key: 'status',
        name: 'Status',
        ariaLabel: 'Status of the request',
        minWidth: 70,
        isResizable: true,
        fieldName: 'status',
        columnActionsMode: ColumnActionsMode.hasDropdown,
        isSorted: orderBy === 'status',
        isSortedDescending: !orderAscending,
        onColumnClick: (ev, column) => openContextMenu(column, ev, Object.values(AirlockRequestStatus)),
        onColumnContextMenu: (column, ev) =>
          (column && ev) && openContextMenu(column, ev, Object.values(AirlockRequestStatus)),
        isFiltered: filters.has('status')
      },
      {
        key: 'createdTime',
        name: 'Created',
        ariaLabel: 'When the request was created',
        minWidth: 120,
        data: 'number',
        isResizable: true,
        fieldName: 'createdTime',
        isSorted: orderBy === 'createdTime',
        isSortedDescending: !orderAscending,
        onRender: (request: AirlockRequest) => {
          return <span>{ moment.unix(request.creationTime).format('DD/MM/YYYY') }</span>;
        },
        onColumnClick: orderByColumn
      },
      {
        key: 'updatedWhen',
        name: 'Updated',
        ariaLabel: 'When the request was last updated',
        minWidth: 120,
        data: 'number',
        isResizable: true,
        fieldName: 'updatedWhen',
        isSorted: orderBy === 'updatedWhen',
        isSortedDescending: !orderAscending,
        onRender: (request: AirlockRequest) => {
          return <span>{ moment.unix(request.updatedWhen).fromNow() }</span>;
        },
        onColumnClick: orderByColumn
      }
    ];
    setRequestColumns(columns);
  }, [openContextMenu, filters, orderAscending, orderBy]);

  const updateRequest = (updatedRequest: AirlockRequest) => {
    setAirlockRequests(requests => {
      const i = requests.findIndex(r => r.id === updatedRequest.id);
      const updatedRequests = [...requests];
      updatedRequests[i] = updatedRequest;
      return updatedRequests;
    });
  };

  const handleNewRequest = (newRequest: AirlockRequest) => {
    setAirlockRequests(requests => [...requests, newRequest]);
    navigate(newRequest.id);
  };

  return (
    <>
      <Stack className="tre-panel">
        <Stack.Item>
          <Stack horizontal horizontalAlign="space-between">
            <h1 style={{marginBottom: '0px'}}>Airlock</h1>
            <CommandBarButton
              iconProps={{ iconName: 'add' }}
              text="New request"
              style={{ background: 'none', color: theme.palette.themePrimary }}
              onClick={() => navigate('new')}
            />
          </Stack>
        </Stack.Item>
      </Stack>
      {
        apiError && <ExceptionLayout e={apiError} />
      }
      <div className="tre-resource-panel" style={{padding: '0px'}}>
        <ShimmeredDetailsList
          items={airlockRequests}
          columns={requestColumns}
          selectionMode={SelectionMode.none}
          getKey={(item) => item?.id}
          onItemInvoked={(item) => navigate(item.id)}
          className="tre-table-rows-align-centre"
          enableShimmer={loadingState === LoadingState.Loading}
        />
        {
          contextMenuProps && <ContextualMenu {...contextMenuProps}/>
        }
        {
          airlockRequests.length === 0 && loadingState !== LoadingState.Loading && <div style={{textAlign: 'center', padding: '50px 10px 100px 10px'}}>
            <h4>No requests found</h4>
            {
              filters.size > 0
                ? <small>There are no requests matching your selected filter(s).</small>
                : <small>Looks like there are no airlock requests yet. Create a new request to get started.</small>
            }
          </div>
        }
      </div>

      <Routes>
        <Route path="new" element={
          <AirlockNewRequest onCreateRequest={handleNewRequest}/>
        } />
        <Route path=":requestId" element={
          <AirlockViewRequest requests={airlockRequests} onUpdateRequest={updateRequest}/>
        } />
      </Routes>
    </>
  );

};

