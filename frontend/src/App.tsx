import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import './App.css';
import type {
  HistoryResponse,
  SnapshotHistoryEntry,
  SnapshotRequestBody,
  SnapshotResponse,
  SnapshotResult,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const parseUrls = (value: string) =>
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

const isValidUrl = (value: string) => {
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
};

const buildSnapshotUrl = (relative?: string | null, absolute?: string | null) => {
  if (relative) {
    try {
      return new URL(relative, API_BASE_URL).toString();
    } catch {
      // ignore malformed base
    }
  }
  return absolute ?? '';
};

const copyText = async (text: string) => {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  // Fallback for browsers/contexts without Clipboard API (some headless deployments)
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  try {
    const success = document.execCommand('copy');
    return success;
  } catch {
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
};

function App() {
  const [urlsText, setUrlsText] = useState('');
  const [forceBrowser, setForceBrowser] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [results, setResults] = useState<SnapshotResult[]>([]);
  const [history, setHistory] = useState<SnapshotHistoryEntry[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [selectedHistoryIds, setSelectedHistoryIds] = useState<Set<string>>(new Set());

  const urls = useMemo(() => parseUrls(urlsText), [urlsText]);
  const invalidUrls = urls.filter((url) => !isValidUrl(url));
  const canSubmit = urls.length > 0 && invalidUrls.length === 0 && !isSubmitting;

  const selectableHistory = useMemo(
    () => history.filter((entry) => Boolean(entry.archived_relative_url)),
    [history],
  );
  const selectableIds = useMemo(() => selectableHistory.map((entry) => entry.id), [selectableHistory]);

  useEffect(() => {
    setSelectedHistoryIds((prev) => {
      const next = new Set<string>();
      selectableIds.forEach((id) => {
        if (prev.has(id)) {
          next.add(id);
        }
      });
      return next;
    });
  }, [history, selectableIds]);

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/history?limit=100`);
      if (!response.ok) {
        throw new Error('无法获取历史记录 / Failed to load history');
      }
      const data: HistoryResponse = await response.json();
      setHistory(data.items);
      setHistoryError(null);
    } catch (error) {
      console.error(error);
      setHistoryError(
        error instanceof Error ? error.message : '历史记录加载失败 / Unable to load history.'
      );
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setRequestError(null);
    setFormError(null);
    setCopyMessage(null);

    if (urls.length === 0) {
      setFormError('请至少输入一个有效的 URL。 / Please enter at least one valid URL.');
      return;
    }
    if (invalidUrls.length > 0) {
      setFormError(`发现 ${invalidUrls.length} 个无效 URL。 / ${invalidUrls.length} invalid URLs found.`);
      return;
    }

    setIsSubmitting(true);
    const body: SnapshotRequestBody = {
      urls,
      force_browser: forceBrowser,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/snapshots`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`请求失败，状态码 ${response.status}`);
      }

      const data: SnapshotResponse = await response.json();
      setResults(data.results);
      await fetchHistory();
    } catch (error) {
      console.error(error);
      setRequestError(
        error instanceof Error
          ? error.message
          : '请求失败，请稍后再试。 / Request failed, please try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleHistorySelection = (id: string) => {
    setSelectedHistoryIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelectedHistoryIds((prev) => {
      if (prev.size === selectableIds.length) {
        return new Set();
      }
      return new Set(selectableIds);
    });
  };

  const copyLinks = async (ids: string[]) => {
    const links = history
      .filter((entry) => ids.includes(entry.id))
      .map((entry) => buildSnapshotUrl(entry.archived_relative_url, entry.archived_url))
      .filter((value) => Boolean(value));

    if (links.length === 0) {
      setCopyMessage('没有可复制的链接 / No links to copy.');
      return;
    }

    const text = links.join('\n');
    try {
      const success = await copyText(text);
      if (!success) {
        throw new Error('Clipboard API unavailable');
      }
      setCopyMessage(`已复制 ${links.length} 条链接 / Copied ${links.length} link(s).`);
    } catch (error) {
      console.error(error);
      setCopyMessage('复制失败 / Copy failed.');
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <h1>PageCopy 网页转存工具</h1>
        <p>输入 URL 即可生成静态快照，支持部分 JS 动态页面。</p>
        <p className="hero-subtitle">Capture multi-language snapshots for long-term preservation.</p>
      </header>

      <section className="panel">
        <form onSubmit={handleSubmit} className="snapshot-form">
          <label htmlFor="url-input">
            URL 列表（每行一个）
            <span className="helper">Multiple URLs, one per line.</span>
          </label>
          <textarea
            id="url-input"
            placeholder={'https://example.com/article\nhttps://mp.weixin.qq.com/s/...'}
            value={urlsText}
            onChange={(event) => setUrlsText(event.target.value)}
            rows={6}
          />

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={forceBrowser}
              onChange={(event) => setForceBrowser(event.target.checked)}
            />
            <span>对 JS 动态页面强制使用浏览器渲染（较慢）</span>
          </label>

          {formError && <p className="form-error">{formError}</p>}
          {requestError && <p className="form-error">{requestError}</p>}

          <button type="submit" disabled={!canSubmit}>
            {isSubmitting ? '处理中...' : '开始转存'}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="results-header">
          <h2>转存结果 / Snapshot Results</h2>
          <p>{results.length === 0 ? '尚未有结果，提交后查看这里。' : `共 ${results.length} 条结果。`}</p>
        </div>
        {results.length > 0 ? (
          <div className="results-table-wrapper">
            <table className="results-table">
              <thead>
                <tr>
                  <th>Original URL</th>
                  <th>Status</th>
                  <th>Archived URL</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {results.map((result, index) => (
                  <tr key={`${result.original_url}-${index}`}>
                    <td>
                      <a href={result.original_url} target="_blank" rel="noreferrer">
                        {result.original_url}
                      </a>
                    </td>
                    <td>
                      <span className={`status-pill ${result.status}`}>{result.status}</span>
                    </td>
                    <td>
                      {result.archived_relative_url || result.archived_url ? (
                        <a
                          href={buildSnapshotUrl(result.archived_relative_url, result.archived_url)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          打开快照
                        </a>
                      ) : (
                        <span className="muted">--</span>
                      )}
                    </td>
                    <td>
                      {result.error ? (
                        <span className="error-text">{result.error}</span>
                      ) : (
                        <span className="muted">--</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="helper">提交后将显示快照链接与错误信息。</p>
        )}
      </section>

      <section className="panel">
        <div className="results-header">
          <h2>历史记录 / Snapshot History</h2>
          <p>保留最近的执行记录，便于再次访问或复制链接。</p>
        </div>
        {historyError && <p className="form-error">{historyError}</p>}
        <div className="history-actions">
          <div className="history-buttons">
            <button type="button" onClick={toggleSelectAll} disabled={selectableIds.length === 0}>
              {selectedHistoryIds.size === selectableIds.length ? '取消全选' : '全选'}
            </button>
            <button
              type="button"
              onClick={() => copyLinks(Array.from(selectedHistoryIds))}
              disabled={selectedHistoryIds.size === 0}
            >
              复制选中
            </button>
            <button
              type="button"
              onClick={() => copyLinks(selectableIds)}
              disabled={selectableIds.length === 0}
            >
              复制全部可用链接
            </button>
            <button type="button" onClick={fetchHistory}>
              刷新
            </button>
          </div>
          {copyMessage && <p className="copy-feedback">{copyMessage}</p>}
        </div>
        {history.length > 0 ? (
          <div className="results-table-wrapper">
            <table className="results-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      checked={selectableIds.length > 0 && selectedHistoryIds.size === selectableIds.length}
                      onChange={() => toggleSelectAll()}
                      aria-label="Select all"
                    />
                  </th>
                  <th>Captured</th>
                  <th>Original URL</th>
                  <th>Archived</th>
                  <th>Status</th>
                  <th>Error</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {history.map((entry) => {
                  const absoluteUrl = buildSnapshotUrl(entry.archived_relative_url, entry.archived_url);
                  const canSelect = Boolean(entry.archived_relative_url);
                  return (
                    <tr key={entry.id}>
                      <td>
                        <input
                          type="checkbox"
                          disabled={!canSelect}
                          checked={selectedHistoryIds.has(entry.id)}
                          onChange={() => toggleHistorySelection(entry.id)}
                        />
                      </td>
                      <td>{new Date(entry.captured_at).toLocaleString()}</td>
                      <td>
                        <a href={entry.original_url} target="_blank" rel="noreferrer">
                          {entry.original_url}
                        </a>
                      </td>
                      <td>
                        {entry.archived_relative_url ? (
                          <a href={absoluteUrl} target="_blank" rel="noreferrer">
                            {entry.archived_relative_url}
                          </a>
                        ) : (
                          <span className="muted">--</span>
                        )}
                      </td>
                      <td>
                        <span className={`status-pill ${entry.status}`}>{entry.status}</span>
                      </td>
                      <td>
                        {entry.error ? <span className="error-text">{entry.error}</span> : <span className="muted">--</span>}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="copy-inline"
                          disabled={!entry.archived_relative_url}
                          onClick={() => copyLinks([entry.id])}
                        >
                          复制链接
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="helper">暂无历史记录，转存完成后会出现在这里。</p>
        )}
      </section>
    </div>
  );
}

export default App;
