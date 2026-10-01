import React from 'react';
import MDXComponents from '@theme-original/MDXComponents';

function KeyboardTable(props) {
  return <table {...props} tabIndex={0} />;
}

export default {...MDXComponents, table: KeyboardTable};
